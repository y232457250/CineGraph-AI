"""
搜索路由 - 处理台词搜索
"""
from fastapi import APIRouter, HTTPException
from typing import Dict

from app.ingestion.vectorizer import Vectorizer

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/lines")
async def search_lines(request: dict):
    """搜索台词"""
    try:
        query = request.get("query", "")
        limit = request.get("limit", 10)
        filters = request.get("filters")
        
        vectorizer = Vectorizer()
        results = vectorizer.search(
            query=query,
            n_results=limit,
            filters=filters
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next-line")
async def search_next_line(request: dict):
    """搜索能接的下一句台词"""
    try:
        current_line_id = request.get("current_line_id")
        limit = request.get("limit", 10)
        
        vectorizer = Vectorizer()
        results = vectorizer.find_next_lines(
            current_line_id=current_line_id,
            n_results=limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
