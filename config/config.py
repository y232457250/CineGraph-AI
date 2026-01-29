# config/config.py
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 数据路径
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MEDIA_DIR = os.path.join(DATA_DIR, "media")
SUBTITLES_DIR = os.path.join(MEDIA_DIR, "subtitles")
VIDEOS_DIR = os.path.join(MEDIA_DIR, "videos")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")

# 模型配置
EMBEDDING_MODEL = "Qwen3-Embedding-4B"
ANNOTATION_MODEL = "Qwen3-4B"

# API配置
EMBEDDING_API_URL = "http://localhost:8000/v1/embeddings"
ANNOTATION_API_URL = "http://localhost:8001/v1/completions"

# ChromaDB配置
CHROMA_COLLECTION = "film_lines"