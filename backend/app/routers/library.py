"""
影片库路由 - 管理已导入的影片
"""
from fastapi import APIRouter, HTTPException, Request
from pathlib import Path
from typing import Dict
import json

from app.core.store import get_store

router = APIRouter(prefix="/api/library", tags=["library"])
store = get_store()


def scan_annotation_files() -> Dict:
    """扫描annotations文件夹，返回已标注的movie_id集合"""
    current_file = Path(__file__).resolve()
    annotations_dir = current_file.parent.parent.parent / "data" / "annotations"
    annotated = {}
    
    if annotations_dir.exists():
        for f in annotations_dir.glob("*_annotated.json"):
            movie_id = f.stem.replace("_annotated", "")
            annotated[movie_id] = str(f)
    
    return annotated


@router.get("/list")
async def list_library():
    """列出影片库中的所有影片，并关联标注状态"""
    try:
        movies = store.list_movies()
        annotated_files = scan_annotation_files()
        
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
                        if ep.get('subtitle_path'):
                            all_annotated = False
                
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


@router.delete("/delete/{movie_id}")
async def delete_from_library(movie_id: str):
    """从影片库中删除指定影片"""
    try:
        movies = store.list_movies()
        original_count = len(movies)
        movies = [m for m in movies if m.get('douban_id') != movie_id]
        
        if len(movies) == original_count:
            raise HTTPException(status_code=404, detail="未找到该影片")
        
        store.save_movies(movies, merge=False)
        return {"status": "ok", "deleted": movie_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-episode/{movie_id}/{episode_number}")
async def delete_episode_from_library(movie_id: str, episode_number: int):
    """从影片库中删除指定影片的某一集"""
    try:
        movies = store.list_movies()
        
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
        
        store.save_movies(movies, merge=False)
        return {"status": "ok", "deleted_episode": episode_number, "remaining_episodes": len(episodes)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/{movie_id}")
async def update_library_item(movie_id: str, request: Request):
    """更新影片库中的指定影片信息"""
    try:
        update_data = await request.json()
        movies = store.list_movies()
        
        found = False
        for i, m in enumerate(movies):
            if m.get('douban_id') == movie_id:
                movies[i].update(update_data)
                found = True
                break
        
        if not found:
            raise HTTPException(status_code=404, detail="未找到该影片")
        
        store.save_movies(movies)
        return {"status": "ok", "updated": movie_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
