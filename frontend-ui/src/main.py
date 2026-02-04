from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
import re
import sys
import json
import threading
import subprocess
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import unquote

# 将当前目录（backend）加入到 Python 路径中，确保 app 模块可以被导入
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from app.database import metadata_store
from app.ingestion import enricher

# 语义标注和向量化模块
try:
    from app.ingestion.semantic_annotator import SemanticAnnotator, LLMProviderManager
    from app.ingestion.vectorizer import Vectorizer
    ANNOTATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 语义标注模块加载失败: {e}")
    ANNOTATION_AVAILABLE = False

# --- 1. 定义数据模型 ---
class ScanRequest(BaseModel):
    path: str

class AnnotateRequest(BaseModel):
    movie_id: str
    subtitle_path: str
    movie_name: str = ""
    llm_provider: str = None

class VectorizeRequest(BaseModel):
    annotation_file: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Dict = None

class NextLineRequest(BaseModel):
    current_line_id: str
    limit: int = 10

# 全局状态
annotation_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_movie": "",
    "error": None
}

vectorize_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "error": None
}

# --- 2. 扫描器逻辑 (直接整合在这里方便调试) ---

# ffmpeg 路径配置（支持项目内置的 ffmpeg）
FFMPEG_PATH = Path(__file__).resolve().parent.parent / "ffmpeg" / "bin" / "ffmpeg.exe"
if not FFMPEG_PATH.exists():
    # 回退到系统 PATH 中的 ffmpeg
    FFMPEG_PATH = "ffmpeg"
else:
    FFMPEG_PATH = str(FFMPEG_PATH)

def extract_video_thumbnail(video_path: str, output_path: str) -> bool:
    """使用 ffmpeg 截取视频首帧作为封面"""
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-ss', '00:00:01',  # 跳过第1秒（避免纯黑帧）
            '-vframes', '1',
            '-q:v', '2',  # 较高质量
            '-y',  # 覆盖已有文件
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return Path(output_path).exists()
    except Exception as e:
        print(f"截取视频封面失败: {e}")
        return False

class MediaScanner:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        # 匹配格式: "豆瓣ID-名字" 或 "豆瓣ID 名字"
        self.folder_pattern = re.compile(r'^(\d+)[-\s]+(.+)$')
        self.video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.ts'}
        self.sub_exts = {'.srt', '.ass', '.vtt'}
        # 匹配集数的模式：E01, EP01, 第01集, S01E01 等
        self.episode_pattern = re.compile(r'[Ee][Pp]?(\d+)|第(\d+)[集话]|[Ss]\d+[Ee](\d+)', re.IGNORECASE)

    def extract_episode_number(self, filename: str) -> int:
        """从文件名中提取集数"""
        match = self.episode_pattern.search(filename)
        if match:
            # 返回第一个非空的匹配组
            for group in match.groups():
                if group:
                    return int(group)
        return 0

    def scan(self):
        results = []
        if not self.base_path.exists():
            return []

        for folder_name in os.listdir(self.base_path):
            folder_path = self.base_path / folder_name
            if not folder_path.is_dir():
                continue

            # 尝试匹配豆瓣ID格式
            match = self.folder_pattern.match(folder_name)
            if match:
                douban_id = match.group(1)
                movie_name = match.group(2).strip()
                is_custom_folder = False
            else:
                # 非豆瓣ID格式的文件夹，使用文件夹名称的哈希值生成稳定的ID
                # 这样同一个文件夹每次扫描都会得到相同的ID，避免重复导入
                folder_hash = hashlib.md5(folder_name.encode('utf-8')).hexdigest()[:8]
                douban_id = f"custom_{folder_hash}"
                movie_name = folder_name.strip()
                is_custom_folder = True
                
            # 收集所有视频和字幕文件（支持电视剧多集情况）
            video_files = []
            subtitle_files = []
            
            # 遍历文件夹内的文件（包括子目录，支持电视剧分季/分集结构）
            try:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in self.video_exts:
                            video_files.append(str(file_path))
                        elif file_path.suffix.lower() in self.sub_exts:
                            subtitle_files.append(str(file_path))
            except Exception as e:
                print(f"读取文件夹 {folder_name} 出错: {e}")
            
            # 判断是电影还是电视剧
            # 规则：多个视频或多个字幕 = 电视剧，单个文件 = 电影
            total_files = max(len(video_files), len(subtitle_files))
            media_type = "tv" if total_files > 1 else "movie"
            
            # 构建 episodes 数组
            episodes = []
            
            # 为每个视频文件创建集数映射
            video_episode_map = {}
            for vf in video_files:
                ep_num = self.extract_episode_number(Path(vf).stem)
                video_episode_map[vf] = ep_num
            
            # 为每个字幕文件创建集数映射
            subtitle_episode_map = {}
            for sf in subtitle_files:
                ep_num = self.extract_episode_number(Path(sf).stem)
                subtitle_episode_map[sf] = ep_num
            
            if media_type == "tv":
                # 电视剧：创建剧集列表，合并视频和字幕文件
                used_subtitles = set()  # 记录已匹配的字幕文件
                
                if video_files:
                    # 有视频文件的情况，先按视频文件来组织
                    sorted_videos = sorted(video_files, key=lambda x: (video_episode_map.get(x, 0), Path(x).stem.lower()))
                
                    for idx, video_path in enumerate(sorted_videos):
                        ep_num = video_episode_map.get(video_path, 0)
                        video_stem = Path(video_path).stem.lower()
                        
                        # 尝试匹配对应的字幕文件
                        matched_subtitle = None
                        for sub_path in subtitle_files:
                            if sub_path in used_subtitles:
                                continue
                            sub_stem = Path(sub_path).stem.lower()
                            # 匹配条件：文件名相似或集数相同
                            if video_stem == sub_stem or video_stem in sub_stem or sub_stem in video_stem:
                                matched_subtitle = sub_path
                                used_subtitles.add(sub_path)
                                break
                            sub_ep_num = self.extract_episode_number(Path(sub_path).stem)
                            if ep_num > 0 and sub_ep_num > 0 and sub_ep_num == ep_num:
                                matched_subtitle = sub_path
                                used_subtitles.add(sub_path)
                                break
                        
                        episodes.append({
                            "episode_number": idx + 1,
                            "video_path": video_path,
                            "subtitle_path": matched_subtitle,
                            "video_filename": Path(video_path).name,
                            "subtitle_filename": Path(matched_subtitle).name if matched_subtitle else None
                        })
                    
                    # 添加未匹配的字幕文件（没有对应视频的字幕）
                    unmatched_subtitles = [sf for sf in subtitle_files if sf not in used_subtitles]
                    for sub_path in sorted(unmatched_subtitles, key=lambda x: (subtitle_episode_map.get(x, 0), Path(x).stem.lower())):
                        episodes.append({
                            "episode_number": len(episodes) + 1,
                            "video_path": None,
                            "subtitle_path": sub_path,
                            "video_filename": None,
                            "subtitle_filename": Path(sub_path).name
                        })
                else:
                    # 只有字幕文件的情况
                    sorted_subtitles = sorted(subtitle_files, key=lambda x: (subtitle_episode_map.get(x, 0), Path(x).stem.lower()))
                    for idx, sub_path in enumerate(sorted_subtitles):
                        episodes.append({
                            "episode_number": idx + 1,
                            "video_path": None,
                            "subtitle_path": sub_path,
                            "video_filename": None,
                            "subtitle_filename": Path(sub_path).name
                        })
                
                # 重新编号剧集，确保顺序正确
                for idx, ep in enumerate(episodes):
                    ep["episode_number"] = idx + 1
            
            # 跳过空文件夹（没有视频也没有字幕）
            if not video_files and not subtitle_files:
                continue
                
            # 取第一个视频和字幕作为代表
            video_file = video_files[0] if video_files else None
            subtitle_file = subtitle_files[0] if subtitle_files else None
            
            # 对于非豆瓣ID文件夹，尝试截取视频首帧作为封面
            local_poster = None
            if is_custom_folder and video_file:
                poster_path = folder_path / "poster.jpg"
                if not poster_path.exists():
                    if extract_video_thumbnail(video_file, str(poster_path)):
                        local_poster = str(poster_path)
                        print(f"✓ 已截取视频首帧作为封面: {poster_path.name}")
                else:
                    local_poster = str(poster_path)
            
            result_item = {
                "douban_id": douban_id,
                "title": movie_name,
                "folder": folder_name,
                "video_path": video_file,
                "subtitle_path": subtitle_file,
                "video_count": len(video_files),
                "subtitle_count": len(subtitle_files),
                "media_type": media_type,
                "episodes": episodes if media_type == "tv" else [],
                "status": "ready" if video_file or subtitle_file else "missing_files",
                "is_custom": is_custom_folder  # 标记是否为自定义文件夹
            }
            
            # 添加本地封面路径
            if local_poster:
                result_item["local_poster"] = local_poster
                
            results.append(result_item)
        return results

# --- 3. 创建 FastAPI 应用 ---
app = FastAPI()

# 配置 CORS，允许 Tauri 前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境下建议设置为具体地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
try:
    from app.api.llm import router as llm_router
    from app.api.config import router as config_router
    from app.api.settings import router as settings_router
    app.include_router(llm_router)
    app.include_router(config_router)
    app.include_router(settings_router)
    print("✅ LLM、Config 和 Settings API 路由已注册")
except ImportError as e:
    print(f"⚠️ API 路由加载失败: {e}")

@app.get("/")
async def root():
    return {"message": "CineGraph-AI Backend is running"}

@app.get("/api/poster/{poster_path:path}")
async def get_poster(poster_path: str):
    """返回本地海报图片"""
    # 解码 URL 编码的路径
    decoded_path = unquote(poster_path)
    poster_file = Path(decoded_path)
    
    if not poster_file.exists():
        raise HTTPException(status_code=404, detail="Poster not found")
    
    if not poster_file.is_file():
        raise HTTPException(status_code=400, detail="Invalid poster path")
    
    # 安全检查：确保是图片文件
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    if poster_file.suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    return FileResponse(poster_file, media_type="image/jpeg")

@app.get("/api/ingest/list")
async def list_movies():
    """返回当前数据库中的所有影片记录"""
    return {"movies": metadata_store.load_movies()}

@app.post("/api/ingest/scan")
async def scan_directory(request: ScanRequest):
    print(f"收到扫描请求路径: {request.path}")
    if not os.path.exists(request.path):
        raise HTTPException(status_code=400, detail="所选路径不存在")
    
    scanner = MediaScanner(request.path)
    movies = scanner.scan()
    
    # 获取已存在的影片记录，用于比较
    existing_movies = metadata_store.load_movies()
    existing_map = {m.get('douban_id'): m for m in existing_movies}
    
    # 标记每个扫描结果的状态：new（新增）、updated（有更新）、unchanged（无变化）
    for movie in movies:
        movie_id = movie.get('douban_id')
        if movie_id not in existing_map:
            movie['_scan_status'] = 'new'
        else:
            # 比较文件数量是否有变化
            existing = existing_map[movie_id]
            old_video_count = existing.get('video_count', 0)
            old_subtitle_count = existing.get('subtitle_count', 0)
            old_episode_count = len(existing.get('episodes', []))
            
            new_video_count = movie.get('video_count', 0)
            new_subtitle_count = movie.get('subtitle_count', 0)
            new_episode_count = len(movie.get('episodes', []))
            
            if (new_video_count != old_video_count or 
                new_subtitle_count != old_subtitle_count or
                new_episode_count != old_episode_count):
                movie['_scan_status'] = 'updated'
            else:
                movie['_scan_status'] = 'unchanged'
    
    new_count = sum(1 for m in movies if m.get('_scan_status') == 'new')
    updated_count = sum(1 for m in movies if m.get('_scan_status') == 'updated')
    unchanged_count = sum(1 for m in movies if m.get('_scan_status') == 'unchanged')
    
    print(f"扫描完成，共 {len(movies)} 部：新增 {new_count}，更新 {updated_count}，无变化 {unchanged_count}")
    return {
        "movies": movies, 
        "total": len(movies),
        "new_count": new_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count
    }


# ==================== 影片库API ====================

def scan_annotation_files() -> dict:
    """扫描annotations文件夹，返回已标注的movie_id集合"""
    annotations_dir = Path(__file__).parent / "data" / "annotations"
    annotated = {}
    
    if annotations_dir.exists():
        for f in annotations_dir.glob("*_annotated.json"):
            # 提取movie_id (去掉_annotated后缀)
            movie_id = f.stem.replace("_annotated", "")
            annotated[movie_id] = str(f)
    
    return annotated


@app.get("/api/library/list")
async def list_library():
    """列出影片库中的所有影片，并关联标注状态"""
    try:
        movies = metadata_store.load_movies()
        
        # 扫描已标注的文件
        annotated_files = scan_annotation_files()
        
        # 为每个影片/剧集关联标注状态
        for movie in movies:
            movie_id = movie.get('douban_id', '')
            
            # 电视剧：检查每集的标注状态
            if movie.get('media_type') == 'tv' and movie.get('episodes'):
                all_annotated = True
                any_annotated = False
                
                for ep in movie.get('episodes', []):
                    ep_id = f"{movie_id}_ep{ep.get('episode_number', 0)}"
                    if ep_id in annotated_files:
                        ep['annotation_path'] = annotated_files[ep_id]
                        any_annotated = True
                    else:
                        if ep.get('subtitle_path'):  # 只有有字幕的才算未标注
                            all_annotated = False
                
                # 整体标注状态
                if any_annotated:
                    movie['status_annotate'] = 'done' if all_annotated else 'partial'
                else:
                    movie['status_annotate'] = 'pending'
                    
            else:
                # 电影：检查单个标注状态
                if movie_id in annotated_files:
                    movie['annotation_path'] = annotated_files[movie_id]
                    movie['status_annotate'] = 'done'
                else:
                    movie['status_annotate'] = 'pending'
        
        return {"items": movies, "total": len(movies)}
    except Exception as e:
        print(f"加载影片库失败: {e}")
        return {"items": [], "total": 0}


@app.delete("/api/library/delete/{movie_id}")
async def delete_from_library(movie_id: str):
    """从影片库中删除指定影片"""
    try:
        movies = metadata_store.load_movies()
        original_count = len(movies)
        movies = [m for m in movies if m.get('douban_id') != movie_id]
        
        if len(movies) == original_count:
            raise HTTPException(status_code=404, detail="未找到该影片")
        
        metadata_store.save_movies(movies, merge_existing=False)
        return {"status": "ok", "deleted": movie_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/library/delete-episode/{movie_id}/{episode_number}")
async def delete_episode_from_library(movie_id: str, episode_number: int):
    """从影片库中删除指定影片的某一集"""
    try:
        movies = metadata_store.load_movies()
        
        found_movie = None
        for m in movies:
            if m.get('douban_id') == movie_id:
                found_movie = m
                break
        
        if not found_movie:
            raise HTTPException(status_code=404, detail="未找到该影片")
        
        episodes = found_movie.get('episodes', [])
        original_count = len(episodes)
        episodes = [ep for ep in episodes if ep.get('episode_number') != episode_number]
        
        if len(episodes) == original_count:
            raise HTTPException(status_code=404, detail="未找到该集")
        
        found_movie['episodes'] = episodes
        found_movie['video_count'] = len(episodes)
        
        metadata_store.save_movies(movies, merge_existing=False)
        return {"status": "ok", "deleted_episode": episode_number, "remaining_episodes": len(episodes)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/library/update/{movie_id}")
async def update_library_item(movie_id: str, request: Request):
    """更新影片库中的指定影片信息"""
    try:
        update_data = await request.json()
        movies = metadata_store.load_movies()
        
        found = False
        for i, m in enumerate(movies):
            if m.get('douban_id') == movie_id:
                movies[i].update(update_data)
                found = True
                break
        
        if not found:
            raise HTTPException(status_code=404, detail="未找到该影片")
        
        metadata_store.save_movies(movies)
        return {"status": "ok", "updated": movie_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/import")
async def import_scan_results(request: Request):
    """Persist scanned movies metadata to disk for later processing.

    This endpoint accepts either a raw JSON list of movie objects, or an
    object with a `movies` key containing the list. It returns the saved
    count on success.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Support both `[{}, ...]` and `{ "movies": [ ... ] }`
    if isinstance(payload, dict) and 'movies' in payload:
        movies = payload.get('movies')
    else:
        movies = payload

    if not isinstance(movies, list):
        raise HTTPException(status_code=400, detail="Expected a JSON list of movie objects")

    # 检查是否有新增或更新的内容
    has_changes = any(m.get('_scan_status') in ('new', 'updated') for m in movies)
    
    # 移除临时的扫描状态字段
    for m in movies:
        m.pop('_scan_status', None)

    # Save quickly and start background enrichment (non-blocking)
    try:
        metadata_store.save_movies(movies)
        # 只有在有新增或更新时才启动 enrichment
        if has_changes:
            try:
                enricher.start_enrichment()
            except Exception:
                # don't fail the request if background start fails
                print("Warning: failed to start enricher")
        else:
            print("[*] No changes detected, skipping enrichment")
        return {"status": "ok", "count": len(movies), "enrichment_started": has_changes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/enrich/start")
async def enrich_start():
    """Start background enrichment (fetch Douban metadata for saved movies)."""
    result = enricher.start_enrichment()
    return result


@app.get("/api/ingest/enrich/status")
async def enrich_status():
    """Get enrichment progress status."""
    return enricher.get_status()


@app.post("/api/ingest/import-debug")
async def import_scan_debug(request: Request):
    """Debug endpoint: print raw body bytes and attempt to parse JSON."""
    body = await request.body()
    print(f"DEBUG RAW BODY ({len(body)} bytes):", body[:1000])
    try:
        payload = await request.json()
        print("DEBUG parsed payload type:", type(payload))
    except Exception as e:
        print("DEBUG parse error:", e)
        raise HTTPException(status_code=400, detail="There was an error parsing the body")
    return {"status": "ok", "received_bytes": len(body)}


# ==================== 语义标注API ====================

@app.get("/api/annotation/providers")
async def list_llm_providers():
    """列出所有可用的LLM提供者"""
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="语义标注模块未加载")
    
    manager = LLMProviderManager()
    return {"providers": manager.list_providers()}


@app.post("/api/annotation/test-connection")
async def test_llm_connection(request: dict):
    """测试LLM连接"""
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="语义标注模块未加载")
    
    provider_id = request.get("provider_id")
    if not provider_id:
        return {"success": False, "error": "未指定模型ID"}
    
    try:
        manager = LLMProviderManager()
        provider = manager.get_provider(provider_id)
        
        if not provider:
            return {"success": False, "error": f"未找到模型: {provider_id}"}
        
        # 测试连接 - 发送一个简单的测试请求
        import httpx
        
        base_url = provider.get("base_url", "http://127.0.0.1:11434")
        model = provider.get("model", "qwen3:4b")
        
        # 构建测试请求
        test_url = f"{base_url}/api/generate"
        test_payload = {
            "model": model,
            "prompt": "Hi",
            "stream": False,
            "options": {"num_predict": 1}  # 只生成1个token
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(test_url, json=test_payload)
            
            if response.status_code == 200:
                return {"success": True, "message": f"模型 {model} 连接成功"}
            else:
                error_text = response.text[:200] if response.text else "未知错误"
                return {"success": False, "error": f"连接失败 ({response.status_code}): {error_text}"}
                
    except httpx.TimeoutException:
        return {"success": False, "error": "连接超时，请确保Ollama服务已启动"}
    except httpx.ConnectError:
        return {"success": False, "error": "无法连接到Ollama服务，请确保服务已启动"}
    except Exception as e:
        return {"success": False, "error": f"测试失败: {str(e)}"}


@app.post("/api/annotation/start")
async def start_annotation(request: AnnotateRequest, background_tasks: BackgroundTasks):
    """开始对字幕文件进行语义标注"""
    global annotation_status
    
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="语义标注模块未加载")
    
    if annotation_status["running"]:
        raise HTTPException(status_code=409, detail="标注任务正在运行中")
    
    if not os.path.exists(request.subtitle_path):
        raise HTTPException(status_code=400, detail=f"字幕文件不存在: {request.subtitle_path}")
    
    # 启动后台任务
    background_tasks.add_task(
        run_annotation,
        request.movie_id,
        request.subtitle_path,
        request.movie_name or request.movie_id,
        request.llm_provider
    )
    
    return {"status": "started", "movie_id": request.movie_id}


def run_annotation(movie_id: str, subtitle_path: str, movie_name: str, llm_provider: str = None):
    """后台执行语义标注"""
    global annotation_status
    
    annotation_status = {
        "running": True,
        "progress": 0,
        "total": 0,
        "current_movie": movie_name,
        "error": None
    }
    
    try:
        annotator = SemanticAnnotator(llm_provider=llm_provider)
        
        def progress_callback(current, total):
            annotation_status["progress"] = current
            annotation_status["total"] = total
        
        annotations = annotator.annotate_subtitle_file(
            subtitle_path=subtitle_path,
            movie_name=movie_name,
            window_size=None,
            max_workers=None,
            progress_callback=progress_callback
        )
        
        # 保存结果
        output_dir = Path(__file__).parent / "data" / "annotations"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{movie_id}_annotated.json"
        
        annotator.save_annotations(annotations, str(output_path))
        
        annotation_status["running"] = False
        annotation_status["progress"] = annotation_status["total"]
        
    except Exception as e:
        annotation_status["running"] = False
        annotation_status["error"] = str(e)
        print(f"❌ 标注失败: {e}")


@app.get("/api/annotation/status")
async def get_annotation_status():
    """获取标注进度"""
    return annotation_status


@app.get("/api/annotation/list")
async def list_annotations():
    """列出所有已标注的文件"""
    output_dir = Path(__file__).parent / "data" / "annotations"
    if not output_dir.exists():
        return {"annotations": []}
    
    annotations = []
    for f in output_dir.glob("*_annotated.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
            annotations.append({
                "file": str(f),
                "movie_id": f.stem.replace("_annotated", ""),
                "line_count": len(data),
                "size": f.stat().st_size
            })
        except Exception:
            continue
    
    return {"annotations": annotations}


# ==================== 向量化API ====================

@app.post("/api/vectorize/start")
async def start_vectorize(request: VectorizeRequest, background_tasks: BackgroundTasks):
    """开始向量化标注数据"""
    global vectorize_status
    
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="向量化模块未加载")
    
    if vectorize_status["running"]:
        raise HTTPException(status_code=409, detail="向量化任务正在运行中")
    
    if not os.path.exists(request.annotation_file):
        raise HTTPException(status_code=400, detail=f"标注文件不存在: {request.annotation_file}")
    
    background_tasks.add_task(run_vectorize, request.annotation_file)
    
    return {"status": "started"}


def run_vectorize(annotation_file: str):
    """后台执行向量化"""
    global vectorize_status
    
    vectorize_status = {
        "running": True,
        "progress": 0,
        "total": 0,
        "error": None
    }
    
    try:
        vectorizer = Vectorizer()
        
        def progress_callback(current, total):
            vectorize_status["progress"] = current
            vectorize_status["total"] = total
        
        count = vectorizer.vectorize_annotations(
            annotations_path=annotation_file,
            batch_size=50,
            progress_callback=progress_callback
        )
        
        vectorize_status["running"] = False
        vectorize_status["progress"] = count
        
    except Exception as e:
        vectorize_status["running"] = False
        vectorize_status["error"] = str(e)
        print(f"❌ 向量化失败: {e}")


@app.get("/api/vectorize/status")
async def get_vectorize_status():
    """获取向量化进度"""
    return vectorize_status


@app.get("/api/vectorize/stats")
async def get_vector_stats():
    """获取向量库统计信息"""
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="向量化模块未加载")
    
    try:
        vectorizer = Vectorizer()
        return vectorizer.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 搜索API ====================

@app.post("/api/search/lines")
async def search_lines(request: SearchRequest):
    """搜索台词"""
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="搜索模块未加载")
    
    try:
        vectorizer = Vectorizer()
        results = vectorizer.search(
            query=request.query,
            n_results=request.limit,
            filters=request.filters
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search/next-line")
async def search_next_line(request: NextLineRequest):
    """搜索能接的下一句台词"""
    if not ANNOTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="搜索模块未加载")
    
    try:
        vectorizer = Vectorizer()
        results = vectorizer.find_next_lines(
            current_line_id=request.current_line_id,
            n_results=request.limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 4. 启动服务 ---
if __name__ == "__main__":
    # 使用 127.0.0.1 确保本地稳定访问
    uvicorn.run(app, host="127.0.0.1", port=8000)



    