"""
存储层模块
"""
from .base import MovieStore
from .json_store import JsonMovieStore, get_store, load_movies, save_movies, get_metadata, update_metadata

__all__ = [
    "MovieStore",
    "JsonMovieStore",
    "get_store",
    "load_movies",
    "save_movies",
    "get_metadata",
    "update_metadata"
]
