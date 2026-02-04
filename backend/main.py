"""
CineGraph-AI Backend
简化版 FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from urllib.parse import unquote
import sys

# 添加项目路径
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# 导入路由
from app.routers import (
    ingest_router,
    library_router,
    annotation_router,
    vectorize_router,
    search_router
)

# 尝试导入 LLM 相关路由
try:
    from app.api.llm import router as llm_router
    from app.api.config import router as config_router
    from app.api.settings import router as settings_router
    API_ROUTERS_AVAILABLE = True
except ImportError:
    API_ROUTERS_AVAILABLE = False
    llm_router = None
    config_router = None
    settings_router = None

# 创建 FastAPI 应用
app = FastAPI(
    title="CineGraph-AI",
    description="AI-powered video mashup assistant",
    version="0.1.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 根路由
@app.get("/")
async def root():
    return {"message": "CineGraph-AI Backend is running"}


# 海报图片路由
@app.get("/api/poster/{poster_path:path}")
async def get_poster(poster_path: str):
    """返回本地海报图片"""
    decoded_path = unquote(poster_path)
    poster_file = Path(decoded_path)
    
    if not poster_file.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Poster not found")
    
    if not poster_file.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid poster path")
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    if poster_file.suffix.lower() not in allowed_extensions:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    return FileResponse(poster_file, media_type="image/jpeg")


# 注册业务路由
app.include_router(ingest_router)
app.include_router(library_router)
app.include_router(annotation_router)
app.include_router(vectorize_router)
app.include_router(search_router)

# 注册 API 路由（如果可用）
if API_ROUTERS_AVAILABLE:
    app.include_router(llm_router)
    app.include_router(config_router)
    app.include_router(settings_router)
    print("✅ LLM、Config 和 Settings API 路由已注册")


# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
