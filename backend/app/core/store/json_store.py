"""
JSON 文件存储实现
保持与原有 metadata_store.py 兼容
"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from .base import MovieStore


class JsonMovieStore(MovieStore):
    """JSON 文件存储实现"""
    
    def __init__(self, data_file: Optional[Path] = None):
        if data_file is None:
            self.data_file = Path(__file__).resolve().parents[3] / "data" / "media_index.json"
        else:
            self.data_file = data_file
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self) -> Dict:
        """加载数据文件"""
        if not self.data_file.exists():
            return {"movies": []}
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"movies": []}
    
    def _save_data(self, data: Dict):
        """保存数据到文件"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_movie(self, douban_id: str) -> Optional[Dict[str, Any]]:
        """根据豆瓣ID获取单个影片"""
        movies = self.list_movies()
        for movie in movies:
            if movie.get("douban_id") == douban_id:
                return movie
        return None
    
    def list_movies(self) -> List[Dict[str, Any]]:
        """获取所有影片列表"""
        data = self._load_data()
        return data.get("movies", [])
    
    def save_movie(self, movie: Dict[str, Any]) -> None:
        """保存单个影片"""
        movies = self.list_movies()
        douban_id = movie.get("douban_id")
        
        # 查找是否已存在
        found = False
        for i, m in enumerate(movies):
            if m.get("douban_id") == douban_id:
                movies[i] = movie
                found = True
                break
        
        if not found:
            movies.append(movie)
        
        self._save_data({"movies": movies})
    
    def save_movies(self, movies: List[Dict[str, Any]], merge: bool = True) -> None:
        """批量保存影片"""
        if merge:
            existing = self.list_movies()
            existing_map = {m.get("douban_id"): m for m in existing}
            
            # 更新或添加新影片
            for movie in movies:
                douban_id = movie.get("douban_id")
                if douban_id:
                    existing_map[douban_id] = movie
            
            movies = list(existing_map.values())
        
        self._save_data({"movies": movies})
    
    def delete_movie(self, douban_id: str) -> bool:
        """删除影片"""
        movies = self.list_movies()
        original_count = len(movies)
        movies = [m for m in movies if m.get("douban_id") != douban_id]
        
        if len(movies) < original_count:
            self._save_data({"movies": movies})
            return True
        return False
    
    def update_metadata(self, douban_id: str, metadata: Dict[str, Any]) -> bool:
        """更新影片元数据"""
        movie = self.get_movie(douban_id)
        if movie:
            movie.update(metadata)
            self.save_movie(movie)
            return True
        return False
    
    def search_movies(self, **filters) -> List[Dict[str, Any]]:
        """根据条件搜索影片"""
        movies = self.list_movies()
        results = movies
        
        for key, value in filters.items():
            results = [m for m in results if m.get(key) == value]
        
        return results


# 全局实例（保持向后兼容）
_default_store: Optional[JsonMovieStore] = None


def get_store() -> JsonMovieStore:
    """获取默认存储实例"""
    global _default_store
    if _default_store is None:
        _default_store = JsonMovieStore()
    return _default_store


# 向后兼容的函数
load_movies = lambda: get_store().list_movies()
save_movies = lambda movies, merge_existing=True: get_store().save_movies(movies, merge=merge_existing)
get_metadata = lambda douban_id: get_store().get_movie(douban_id)
update_metadata = lambda douban_id, metadata: get_store().update_metadata(douban_id, metadata)
