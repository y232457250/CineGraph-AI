# backend/app/database/metadata_store.py
"""
影片元数据存储模块 - 基于 SQLite 数据库

此模块提供与旧版 JSON 存储兼容的 API 接口，
但底层使用 SQLite 数据库（通过 unified_store）存储数据。
"""
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from app.core.store.unified_store import get_unified_store


def save_movies(movies: List[Dict], *, merge_existing: bool = True) -> None:
    """
    保存影片元数据到数据库
    
    Args:
        movies: 影片数据列表
        merge_existing: 是否合并已存在的数据（默认为 True）
    """
    store = get_unified_store()
    
    if not merge_existing:
        # 如果不合并，获取当前所有影片ID，删除不在新列表中的
        existing = store.list_movies()
        existing_ids = {m.get('id') or m.get('douban_id') for m in existing}
        new_ids = {str(m.get('douban_id') or m.get('id') or '').strip() for m in movies if m.get('douban_id') or m.get('id')}
        
        # 删除不在新列表中的影片
        for old_id in existing_ids - new_ids:
            if old_id:
                store.delete_movie(old_id)
    
    # 保存/更新每个影片
    for m in movies:
        movie_id = str(m.get('douban_id') or m.get('id') or '').strip()
        if not movie_id:
            continue
        
        # 规范化数据格式
        movie_data = _normalize_movie_data(m, movie_id)
        
        # 保存到数据库
        store.save_movie(movie_data)


def load_movies() -> List[Dict]:
    """
    从数据库加载所有影片元数据
    
    Returns:
        影片数据列表
    """
    store = get_unified_store()
    movies = store.list_movies()
    
    # 转换为兼容旧格式的字典
    result = []
    for m in movies:
        movie_dict = _convert_to_legacy_format(m)
        result.append(movie_dict)
    
    return result


def get_movie(movie_id: str) -> Optional[Dict]:
    """
    获取单个影片数据
    
    Args:
        movie_id: 影片ID（douban_id）
        
    Returns:
        影片数据字典，不存在则返回 None
    """
    store = get_unified_store()
    movie = store.get_movie(movie_id)
    
    if movie:
        return _convert_to_legacy_format(movie)
    return None


def delete_movie(movie_id: str) -> bool:
    """
    删除影片
    
    Args:
        movie_id: 影片ID
        
    Returns:
        是否删除成功
    """
    store = get_unified_store()
    return store.delete_movie(movie_id)


def delete_episode(movie_id: str, episode_number: int) -> Tuple[bool, int]:
    """
    删除影片的某一集
    
    Args:
        movie_id: 影片ID
        episode_number: 集数
        
    Returns:
        (是否成功, 剩余集数)
    """
    store = get_unified_store()
    return store.delete_episode(movie_id, episode_number)


def update_movie(movie_id: str, updates: Dict) -> bool:
    """
    更新影片数据
    
    Args:
        movie_id: 影片ID
        updates: 要更新的字段
        
    Returns:
        是否更新成功
    """
    store = get_unified_store()
    movie = store.get_movie(movie_id)
    
    if not movie:
        return False
    
    # 合并更新
    movie.update(updates)
    movie['id'] = movie_id
    store.save_movie(movie)
    return True


def _normalize_movie_data(m: Dict, movie_id: str) -> Dict:
    """规范化影片数据格式，将扫描结果转换为数据库存储格式"""
    
    # 处理 episodes：扫描结果中电影可能没有 episodes 数据，
    # 但有 video_path/subtitle_path，需要为其创建一个 episode 记录
    episodes = m.get('episodes', [])
    media_type = m.get('media_type', 'movie')
    
    if not episodes and media_type == 'movie':
        # 电影类型且没有 episodes 数据，从顶层 video_path/subtitle_path 创建
        video_path = m.get('video_path')
        subtitle_path = m.get('subtitle_path')
        if video_path or subtitle_path:
            episodes = [{
                'episode_number': 1,
                'video_path': video_path,
                'subtitle_path': subtitle_path,
                'video_filename': Path(video_path).name if video_path else None,
                'subtitle_filename': Path(subtitle_path).name if subtitle_path else None,
            }]
    
    return {
        'id': movie_id,
        'douban_id': movie_id,
        'title': m.get('title', ''),
        'original_title': m.get('original_title'),
        'year': m.get('year'),
        'media_type': media_type,
        'folder': m.get('folder'),
        'folder_path': m.get('folder_path'),
        'poster_url': m.get('poster_url'),
        'local_poster': m.get('local_poster'),
        'director': m.get('director'),
        'writer': m.get('writer'),
        'starring': m.get('starring', []),
        'genre': m.get('genre'),
        'country': m.get('country'),
        'language': m.get('language'),
        'release_date': m.get('release_date'),
        'douban_url': m.get('douban_url'),
        'rating': m.get('rating'),
        'status_import': m.get('status_import', 'done'),  # 导入后默认设为 done
        'status_annotate': m.get('status_annotate', 'pending'),
        'status_vectorize': m.get('status_vectorize', 'pending'),
        'import_batch': m.get('import_batch'),
        'episodes': episodes,
    }


def _convert_to_legacy_format(m: Dict) -> Dict:
    """转换为兼容旧 JSON 格式的字典"""
    return {
        'douban_id': m.get('id') or m.get('douban_id'),
        'title': m.get('title'),
        'original_title': m.get('original_title'),
        'year': m.get('year'),
        'media_type': m.get('media_type', 'movie'),
        'folder': m.get('folder'),
        'folder_path': m.get('folder_path'),
        'video_path': _get_video_path(m),
        'subtitle_path': _get_subtitle_path(m),
        'video_count': _count_videos(m),
        'subtitle_count': _count_subtitles(m),
        'poster_url': m.get('poster_url'),
        'local_poster': m.get('local_poster'),
        'director': m.get('director'),
        'writer': m.get('writer'),
        'starring': m.get('starring', []),
        'genre': m.get('genre'),
        'country': m.get('country'),
        'language': m.get('language'),
        'release_date': m.get('release_date'),
        'douban_url': m.get('douban_url'),
        'rating': m.get('rating'),
        'status_import': m.get('status_import', 'pending'),
        'status_annotate': m.get('status_annotate', 'pending'),
        'status_vectorize': m.get('status_vectorize', 'pending'),
        'episodes': m.get('episodes', []),
        'annotation_path': m.get('annotation_path'),
    }


def _get_video_path(m: Dict) -> Optional[str]:
    """获取影片的主视频路径"""
    episodes = m.get('episodes', [])
    if episodes and len(episodes) > 0:
        return episodes[0].get('video_path')
    return None


def _get_subtitle_path(m: Dict) -> Optional[str]:
    """获取影片的主字幕路径"""
    episodes = m.get('episodes', [])
    if episodes and len(episodes) > 0:
        return episodes[0].get('subtitle_path')
    return None


def _count_videos(m: Dict) -> int:
    """统计视频文件数量"""
    episodes = m.get('episodes', [])
    return sum(1 for ep in episodes if ep.get('video_path'))


def _count_subtitles(m: Dict) -> int:
    """统计字幕文件数量"""
    episodes = m.get('episodes', [])
    return sum(1 for ep in episodes if ep.get('subtitle_path'))
