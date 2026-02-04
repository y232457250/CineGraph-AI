"""
导入模块路由 - 处理媒体扫描、导入、元数据增强
"""
from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict
from pathlib import Path
import os
import sys

# 添加项目路径
current_dir = Path(__file__).resolve().parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from app.database import metadata_store
from app.ingestion import enricher
from app.services.media_scanner import MediaScanner

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.get("/list")
async def list_movies():
    """返回当前数据库中的所有影片记录"""
    return {"movies": metadata_store.load_movies()}


@router.post("/scan")
async def scan_directory(request: Request):
    """扫描目录中的媒体文件"""
    try:
        data = await request.json()
        path = data.get("path")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail="所选路径不存在")
    
    scanner = MediaScanner(path)
    movies = scanner.scan()
    
    # 获取已存在的影片记录，用于比较
    existing_movies = metadata_store.load_movies()
    existing_map = {m.get('douban_id'): m for m in existing_movies}
    
    # 标记每个扫描结果的状态
    for movie in movies:
        movie_id = movie.get('douban_id')
        if movie_id not in existing_map:
            movie['_scan_status'] = 'new'
        else:
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
    
    return {
        "movies": movies, 
        "total": len(movies),
        "new_count": new_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count
    }


@router.post("/import")
async def import_scan_results(request: Request):
    """将扫描结果导入数据库"""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # 支持两种格式
    if isinstance(payload, dict) and 'movies' in payload:
        movies = payload.get('movies')
    else:
        movies = payload
    
    if not isinstance(movies, list):
        raise HTTPException(status_code=400, detail="Expected a JSON list of movie objects")
    
    has_changes = any(m.get('_scan_status') in ('new', 'updated') for m in movies)
    
    # 移除临时状态字段
    for m in movies:
        m.pop('_scan_status', None)
    
    try:
        metadata_store.save_movies(movies)
        if has_changes:
            try:
                enricher.start_enrichment()
            except Exception:
                pass
        return {"status": "ok", "count": len(movies), "enrichment_started": has_changes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich/start")
async def enrich_start():
    """启动后台元数据增强"""
    result = enricher.start_enrichment()
    return result


@router.get("/enrich/status")
async def enrich_status():
    """获取元数据增强状态"""
    return enricher.get_status()
