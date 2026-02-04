"""
语义标注路由 - 处理 LLM 标注任务
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import os
import threading
import json

from app.ingestion.semantic_annotator import SemanticAnnotator, LLMProviderManager

router = APIRouter(prefix="/api/annotation", tags=["annotation"])

# 全局状态
annotation_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_movie": "",
    "error": None
}
annotation_cancel_event = threading.Event()


class AnnotateRequest:
    def __init__(self, **kwargs):
        self.movie_id = kwargs.get("movie_id")
        self.subtitle_path = kwargs.get("subtitle_path")
        self.movie_name = kwargs.get("movie_name", "")
        self.llm_provider = kwargs.get("llm_provider")
        self.batch_size = kwargs.get("batch_size")
        self.concurrent_requests = kwargs.get("concurrent_requests")
        self.max_retries = kwargs.get("max_retries")
        self.save_interval = kwargs.get("save_interval")


@router.get("/providers")
async def list_llm_providers():
    """列出所有可用的LLM提供者"""
    try:
        manager = LLMProviderManager()
        return {"providers": manager.list_providers()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"语义标注模块未加载: {e}")


@router.post("/test-connection")
async def test_llm_connection(request: dict):
    """测试LLM连接"""
    try:
        provider_id = request.get("provider_id")
        if not provider_id:
            return {"success": False, "error": "未指定模型ID"}
        
        manager = LLMProviderManager()
        provider = manager.get_provider(provider_id)
        
        if not provider:
            return {"success": False, "error": f"未找到模型: {provider_id}"}
        
        result = provider.test_connection()
        return result
    except Exception as e:
        return {"success": False, "error": f"测试失败: {str(e)}"}


@router.post("/start")
async def start_annotation(request: dict, background_tasks: BackgroundTasks):
    """开始对字幕文件进行语义标注"""
    global annotation_status
    
    if annotation_status["running"]:
        raise HTTPException(status_code=409, detail="标注任务正在运行中")
    
    subtitle_path = request.get("subtitle_path")
    if not subtitle_path or not os.path.exists(subtitle_path):
        raise HTTPException(status_code=400, detail=f"字幕文件不存在: {subtitle_path}")
    
    annotation_cancel_event.clear()
    background_tasks.add_task(
        run_annotation,
        request.get("movie_id"),
        subtitle_path,
        request.get("movie_name") or request.get("movie_id"),
        request.get("llm_provider"),
        request.get("batch_size"),
        request.get("concurrent_requests"),
        request.get("max_retries"),
        request.get("save_interval")
    )
    
    return {"status": "started", "movie_id": request.get("movie_id")}


def run_annotation(
    movie_id: str, 
    subtitle_path: str, 
    movie_name: str, 
    llm_provider: str = None,
    batch_size: int = None,
    concurrent_requests: int = None,
    max_retries: int = None,
    save_interval: int = None
):
    """后台执行语义标注"""
    global annotation_status
    
    annotation_status = {
        "running": True,
        "progress": 0,
        "total": 0,
        "current_movie": movie_name,
        "error": None
    }
    
    try:
        annotator = SemanticAnnotator(
            llm_provider=llm_provider,
            max_retries=max_retries,
            save_interval=save_interval
        )
        
        def progress_callback(current, total):
            annotation_status["progress"] = current
            annotation_status["total"] = total
        
        print(f"📋 标注参数: batch_size={batch_size}, concurrent={concurrent_requests}")
        
        annotations = annotator.annotate_subtitle_file(
            subtitle_path=subtitle_path,
            movie_name=movie_name,
            movie_id=movie_id,
            window_size=5,
            max_workers=concurrent_requests,
            batch_size=batch_size,
            progress_callback=progress_callback,
            cancel_event=annotation_cancel_event
        )
        
        if annotation_cancel_event.is_set():
            annotation_status["running"] = False
            annotation_status["current_movie"] = "已取消（未保存当前文件）"
            annotation_status["error"] = "已取消"
            return
        
        if annotations and len(annotations) > 0:
            output_dir = Path(__file__).parent.parent.parent / "data" / "annotations"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{movie_id}_annotated.json"
            
            annotator.save_annotations(annotations, str(output_path))
            print(f"✅ 标注已保存: {output_path}")
        
        annotation_status["running"] = False
        annotation_status["progress"] = annotation_status["total"]
        
    except Exception as e:
        annotation_status["running"] = False
        annotation_status["error"] = str(e)
        print(f"❌ 标注失败: {e}")


@router.get("/status")
async def get_annotation_status():
    """获取标注进度"""
    return annotation_status


@router.post("/cancel")
async def cancel_annotation():
    """取消当前标注任务"""
    annotation_cancel_event.set()
    annotation_status["running"] = False
    annotation_status["error"] = "已取消"
    return {"success": True}


@router.get("/list")
async def list_annotations():
    """列出所有已标注的文件"""
    output_dir = Path(__file__).parent.parent.parent / "data" / "annotations"
    if not output_dir.exists():
        return {"annotations": []}
    
    annotations = []
    for f in output_dir.glob("*_annotated.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
            annotations.append({
                "file": str(f),
                "movie_id": f.stem.replace("_annotated", ""),
                "line_count": len(data),
                "size": f.stat().st_size
            })
        except Exception:
            continue
    
    return {"annotations": annotations}
