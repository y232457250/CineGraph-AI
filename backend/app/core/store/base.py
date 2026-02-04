"""
数据存储层抽象基类
支持 JSON 和 SQLite 两种实现
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class MovieStore(ABC):
    """
    影片存储抽象基类
    
    实现类:
    - JsonMovieStore: JSON 文件实现（当前）
    - SQLiteMovieStore: SQLite 数据库实现（未来）
    """
    
    @abstractmethod
    def get_movie(self, douban_id: str) -> Optional[Dict[str, Any]]:
        """根据豆瓣ID获取单个影片"""
        pass
    
    @abstractmethod
    def list_movies(self) -> List[Dict[str, Any]]:
        """获取所有影片列表"""
        pass
    
    @abstractmethod
    def save_movie(self, movie: Dict[str, Any]) -> None:
        """保存单个影片（新增或更新）"""
        pass
    
    @abstractmethod
    def save_movies(self, movies: List[Dict[str, Any]], merge: bool = True) -> None:
        """批量保存影片"""
        pass
    
    @abstractmethod
    def delete_movie(self, douban_id: str) -> bool:
        """删除影片"""
        pass
    
    @abstractmethod
    def update_metadata(self, douban_id: str, metadata: Dict[str, Any]) -> bool:
        """更新影片元数据字段"""
        pass
    
    @abstractmethod
    def search_movies(self, **filters) -> List[Dict[str, Any]]:
        """根据条件搜索影片"""
        pass
