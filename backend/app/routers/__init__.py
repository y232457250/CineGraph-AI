"""
Routers 模块 - API 路由
"""
from .ingest import router as ingest_router
from .library import router as library_router
from .annotation import router as annotation_router
from .vectorize import router as vectorize_router
from .search import router as search_router

__all__ = [
    "ingest_router",
    "library_router", 
    "annotation_router",
    "vectorize_router",
    "search_router"
]
