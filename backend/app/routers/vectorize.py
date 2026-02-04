"""
向量化路由 - 处理向量入库任务
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import List, Dict
import os
import re
import threading

from app.ingestion.vectorizer import Vectorizer
from app.database import metadata_store

router = APIRouter(prefix="/api/vectorize", tags=["vectorize"])

# 全局状态
vectorize_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_movie": "",
    "error": None,
    "queue_progress": {"current": 0, "total": 0}
}
vectorize_cancel_event = threading.Event()


@router.post("/start")
async def start_vectorize(request: dict, background_tasks: BackgroundTasks):
    """开始向量化标注数据"""
    global vectorize_status
    
    if vectorize_status["running"]:
        raise HTTPException(status_code=409, detail="向量化任务正在运行中")
    
    # 收集所有需要向量化的标注文件
    annotation_files = []
    
    # 单文件模式（向后兼容）
    annotation_file = request.get("annotation_file")
    if annotation_file:
        if not os.path.exists(annotation_file):
            raise HTTPException(status_code=400, detail=f"标注文件不存在: {annotation_file}")
        annotation_files.append(annotation_file)
    
    # 批量模式
    current_dir = Path(__file__).parent.parent.parent
    annotations_dir = current_dir / "data" / "annotations"
    
    # 处理电影
    for movie_id in request.get("movie_ids", []):
        pattern = f"{movie_id}_annotated.json"
        matches = list(annotations_dir.glob(pattern))
        if matches:
            annotation_files.append(str(matches[0]))
        else:
            try:
                metadata = metadata_store.get_metadata(movie_id)
                if metadata and metadata.get("annotation_path"):
                    ann_path = metadata["annotation_path"]
                    if os.path.exists(ann_path):
                        annotation_files.append(ann_path)
            except Exception:
                pass
    
    # 处理剧集
    for ep_item in request.get("episode_items", []):
        douban_id = ep_item.get("douban_id")
        episode_number = ep_item.get("episode_number")
        if douban_id and episode_number:
            pattern = f"{douban_id}_ep{episode_number}_annotated.json"
            matches = list(annotations_dir.glob(pattern))
            if matches:
                annotation_files.append(str(matches[0]))
    
    if not annotation_files:
        raise HTTPException(status_code=400, detail="未找到任何标注文件")
    
    provider_id = request.get("provider_id")
    vectorize_cancel_event.clear()
    background_tasks.add_task(run_vectorize_batch, annotation_files, provider_id)
    
    return {"status": "started", "total_files": len(annotation_files)}


def run_vectorize_batch(annotation_files: List[str], provider_id: str = None):
    """后台执行批量向量化"""
    global vectorize_status
    
    total_files = len(annotation_files)
    vectorize_status = {
        "running": True,
        "progress": 0,
        "total": 0,
        "current_movie": "",
        "error": None,
        "queue_progress": {"current": 0, "total": total_files}
    }
    
    try:
        vectorizer = Vectorizer()
        total_count = 0
        
        for idx, annotation_file in enumerate(annotation_files):
            if vectorize_cancel_event.is_set():
                vectorize_status["current_movie"] = "已取消"
                vectorize_status["running"] = False
                return
            
            filename = os.path.basename(annotation_file)
            vectorize_status["current_movie"] = filename
            vectorize_status["queue_progress"]["current"] = idx + 1
            vectorize_status["progress"] = 0
            vectorize_status["total"] = 0
            
            def progress_callback(current, total):
                if vectorize_cancel_event.is_set():
                    raise Exception("向量化已取消")
                vectorize_status["progress"] = current
                vectorize_status["total"] = total
            
            try:
                count = vectorizer.vectorize_annotations(
                    annotations_path=annotation_file,
                    batch_size=50,
                    progress_callback=progress_callback
                )
                
                if vectorize_cancel_event.is_set():
                    vectorize_status["current_movie"] = "已取消（当前文件未完成）"
                    vectorize_status["running"] = False
                    return
                
                total_count += count
                
                # 更新metadata
                base_name = os.path.basename(annotation_file)
                match = re.match(r"(\d+)(?:_ep\d+)?_annotated\.json", base_name)
                if match:
                    douban_id = match.group(1)
                    try:
                        vector_path = annotation_file.replace("_annotated.json", "_vectorized")
                        metadata_store.update_metadata(douban_id, {
                            "status_vectorize": "done",
                            "vector_path": vector_path
                        })
                    except Exception as e:
                        print(f"⚠️ 更新metadata失败: {e}")
                        
            except Exception as e:
                if "已取消" in str(e):
                    vectorize_status["current_movie"] = "已取消（当前文件未完成）"
                    vectorize_status["running"] = False
                    return
                print(f"⚠️ 向量化 {filename} 失败: {e}")
                continue
        
        vectorize_status["running"] = False
        vectorize_status["current_movie"] = f"完成 ({total_count} 条)"
        vectorize_status["queue_progress"]["current"] = total_files
        
    except Exception as e:
        vectorize_status["running"] = False
        vectorize_status["error"] = str(e)
        print(f"❌ 向量化失败: {e}")


@router.post("/cancel")
async def cancel_vectorize():
    """取消向量化任务"""
    if not vectorize_status["running"]:
        return {"status": "not_running"}
    
    vectorize_cancel_event.set()
    return {"status": "cancelling"}


@router.get("/status")
async def get_vectorize_status():
    """获取向量化进度"""
    return vectorize_status


@router.get("/stats")
async def get_vector_stats():
    """获取向量库统计信息"""
    try:
        vectorizer = Vectorizer()
        return vectorizer.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
