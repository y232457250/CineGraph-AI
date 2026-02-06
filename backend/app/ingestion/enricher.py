import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from app.database import metadata_store
import requests
from bs4 import BeautifulSoup
import traceback

# Global task state
TASK: Dict[str, Any] = {
    "status": "idle",  # idle, running, done, error
    "total": 0,
    "processed": 0,
    "current": None,
    "errors": []
}


def normalize_language(languages: list) -> str:
    """将语言列表简化为：中文、英文、其他、或组合"""
    if not languages:
        return "其他"
    
    # 中文相关的语言
    chinese_keywords = ['汉语', '普通话', '国语', '粤语', '闽南语', '上海话', '四川话', 
                        '陕西话', '东北话', '南京话', '吴语', '客家话', '方言', '中文',
                        '台语', '潮汕话', '湖南话', '河南话', '山东话', '云南方言']
    # 英文相关的语言
    english_keywords = ['英语', 'English', '英文']
    
    has_chinese = False
    has_english = False
    
    lang_str = " ".join(languages).lower()
    
    for kw in chinese_keywords:
        if kw.lower() in lang_str:
            has_chinese = True
            break
    
    for kw in english_keywords:
        if kw.lower() in lang_str:
            has_english = True
            break
    
    if has_chinese and has_english:
        return "中文 / 英文"
    elif has_chinese:
        return "中文"
    elif has_english:
        return "英文"
    else:
        return "其他"


def fetch_douban_metadata(douban_id: str):
    """Fetch movie details using Douban's Rexxar API (mobile API)."""
    base_url = f'https://m.douban.com/rexxar/api/v2/movie/{douban_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
        'Referer': f'https://m.douban.com/movie/subject/{douban_id}/',
    }
    params = {'for_mobile': '1'}
    
    try:
        # 1. Get basic info
        resp = requests.get(base_url, headers=headers, params=params, timeout=8)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        
        # 只取前4个演员
        actors = [a['name'] for a in data.get('actors', [])][:4]
        
        info = {
            'title': data.get('title'),
            'genre': " / ".join(data.get('genres', [])),
            'country': " / ".join(data.get('countries', [])),
            'language': normalize_language(data.get('languages', [])),
            'release_date': data.get('pubdate', [None])[0] or data.get('year'),
            'director': ", ".join([d['name'] for d in data.get('directors', [])]),
            'starring': actors,
            'writer': None,
            'douban_url': f'https://movie.douban.com/subject/{douban_id}/',
            'poster_url': data.get('pic', {}).get('large') or data.get('cover_url') or data.get('cover', {}).get('url'),
            'rating': str(data.get('rating', {}).get('value', '')) if data.get('rating', {}).get('value') else None
        }
        
        # 2. Get credits for writers
        credits_url = f'{base_url}/credits'
        c_resp = requests.get(credits_url, headers=headers, timeout=8)
        if c_resp.status_code == 200:
            c_data = c_resp.json()
            writers = []
            seen_writers = set()
            for item in c_data.get('items', []):
                if item.get('category') == '编剧':
                    name = item.get('name')
                    if name and name not in seen_writers:
                        writers.append(name)
                        seen_writers.add(name)
            info['writer'] = ", ".join(writers) if writers else None
            
            # Fallback for starring if main API actors list is empty
            if not info['starring']:
                actors = []
                for item in c_data.get('items', []):
                    if item.get('category') == '演员':
                        name = item.get('name')
                        if name: actors.append(name)
                info['starring'] = actors[:4]
        
        return info
    except Exception as e:
        print(f'ERROR fetching douban Rexxar {douban_id}: {e}')
        return None


def download_poster(poster_url: str, movie_folder: Path, douban_id: str) -> Optional[str]:
    """下载海报图片到电影文件夹，统一命名为 poster.jpg"""
    if not poster_url:
        return None
    
    try:
        # 统一命名为 poster.jpg
        poster_path = movie_folder / 'poster.jpg'
        
        # 如果已存在则跳过
        if poster_path.exists():
            return str(poster_path)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': f'https://movie.douban.com/subject/{douban_id}/',
        }
        
        resp = requests.get(poster_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            with open(poster_path, 'wb') as f:
                f.write(resp.content)
            return str(poster_path)
        else:
            print(f'  -> poster download failed: HTTP {resp.status_code}')
            return None
    except Exception as e:
        print(f'  -> poster download error: {e}')
        return None


def _run_enrichment(target_ids: list = None):
    try:
        print(f"[*] Starting background enrichment...")
        TASK.update({"status": "running", "errors": [], "processed": 0, "current": None})
        all_movies = metadata_store.load_movies()
        
        # 如果指定了 target_ids，只处理这些影片
        if target_ids:
            target_set = set(str(tid) for tid in target_ids)
            movies = [m for m in all_movies if str(m.get('douban_id', '')) in target_set]
            print(f"[*] Targeted enrichment: {len(movies)} / {len(all_movies)} movies")
        else:
            movies = all_movies
        
        TASK["total"] = len(movies)

        for idx, m in enumerate(movies):
            douban_id = str(m.get("douban_id")) if m.get("douban_id") else None
            
            # 跳过非豆瓣ID的自定义文件夹（custom_ 开头）
            if douban_id and douban_id.startswith("custom_"):
                TASK["processed"] = idx + 1
                continue
            
            has_metadata = m.get("director") or m.get("starring")
            
            # 确定电影文件夹路径（优先使用 folder_path，否则从 video_path 推断）
            folder_path = m.get("folder_path")
            if not folder_path:
                video_path = m.get("video_path")
                if video_path:
                    folder_path = str(Path(video_path).parent)
            
            movie_folder = Path(folder_path) if folder_path else None
            poster_file = movie_folder / "poster.jpg" if movie_folder else None
            has_poster = poster_file and poster_file.exists()
            
            # 如果有海报文件但数据库中没有记录，更新记录
            if has_poster and not m.get("local_poster"):
                m["local_poster"] = str(poster_file)
                metadata_store.save_movies([m])
            
            # 如果数据库记录了local_poster但文件已被删除，清除错误记录
            if m.get("local_poster") and not has_poster:
                print(f"[!] Poster file missing for: {m.get('title')}, will re-download")
                m["local_poster"] = None  # 清除错误记录
            
            # Skip if already fully enriched (has metadata AND has local poster)
            if has_metadata and has_poster:
                TASK["processed"] = idx + 1
                continue
            
            # 如果有元数据但没有海报，尝试下载海报
            if has_metadata and not has_poster:
                poster_url = m.get("poster_url")
                # 如果没有 poster_url，需要重新获取
                if not poster_url and douban_id:
                    print(f"[>] Fetching poster_url for: {m.get('title')} ({idx+1}/{len(movies)})")
                    meta = fetch_douban_metadata(douban_id)
                    if meta and meta.get("poster_url"):
                        poster_url = meta.get("poster_url")
                        m["poster_url"] = poster_url
                        # 同时更新其他可能缺失的字段
                        if meta.get("rating") and not m.get("rating"):
                            m["rating"] = meta.get("rating")
                
                if poster_url and movie_folder and movie_folder.exists():
                    print(f"[>] Downloading poster for: {m.get('title')} ({idx+1}/{len(movies)})")
                    local_poster = download_poster(poster_url, movie_folder, douban_id)
                    if local_poster:
                        m['local_poster'] = local_poster
                        print(f" [OK] Poster saved: {local_poster}")
                    metadata_store.save_movies([m])
                    time.sleep(0.5)  # 避免请求太快
                TASK["processed"] = idx + 1
                continue

            TASK["current"] = douban_id
            print(f"[>] Fetching metadata for ID: {douban_id} ({idx+1}/{len(movies)})")
            try:
                if douban_id:
                    meta = fetch_douban_metadata(douban_id)
                    if meta:
                        for k, v in meta.items():
                            if v:
                                m[k] = v
                        
                        # 下载海报到本地
                        poster_url = meta.get('poster_url')
                        if poster_url and movie_folder and movie_folder.exists():
                            local_poster = download_poster(poster_url, movie_folder, douban_id)
                            if local_poster:
                                m['local_poster'] = local_poster
                                print(f" [OK] Poster saved: {local_poster}")
                        
                        print(f" [OK] Fetched: {meta.get('title')}")
                    else:
                        print(f" [!!] Failed to fetch ID: {douban_id}")
                
                TASK["processed"] = idx + 1
                # persist incremental updates
                metadata_store.save_movies([m])
                time.sleep(1.0) # slightly slower to be safe
            except Exception as e:
                print(f" [EX] Error fetching {douban_id}: {e}")
                TASK["errors"].append({"douban_id": douban_id, "error": str(e)})
        
        print("[*] Enrichment completed.")
        TASK["status"] = "done"
        TASK["current"] = None
    except Exception as e:
        print(f"[*] Enrichment task failed: {e}")
        traceback.print_exc()
        TASK["status"] = "error"
        TASK["errors"].append({"error": str(e)})


def start_enrichment(target_ids: list = None) -> Dict:
    if TASK.get("status") == "running":
        return {"status": "running"}
    t = threading.Thread(target=_run_enrichment, args=(target_ids,), daemon=True)
    t.start()
    return {"status": "started"}


def get_status() -> Dict:
    return TASK.copy()
