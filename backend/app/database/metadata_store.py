"""
元数据存储模块
向后兼容的包装，实际实现迁移到 app.core.store
"""
# 重新导出以保持向后兼容
from app.core.store import (
    load_movies,
    save_movies,
    get_metadata,
    update_metadata
)

__all__ = ["load_movies", "save_movies", "get_metadata", "update_metadata"]
