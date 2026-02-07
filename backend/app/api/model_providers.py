# backend/app/api/model_providers.py
"""
模型提供者管理 API
提供模型配置的 CRUD、切换、连接测试等功能
替代原有分散在 llm.py / settings.py / config.py 中的模型管理逻辑
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.model_provider_service import get_model_provider_service

router = APIRouter(prefix="/api/model-providers", tags=["Model Providers"])


# ==================== 数据模型 ====================

class ProviderCreateRequest(BaseModel):
    id: str = ""
    name: str
    category: str  # "llm" 或 "embedding"
    provider_type: str = "commercial"  # "local" 或 "commercial"
    local_mode: str = ""  # "ollama" / "docker" / ""
    base_url: str
    model: str
    api_key: str = ""
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 60
    dimension: int = 0
    api_style: str = "openai"
    description: str = ""
    price_info: str = ""
    sort_order: int = 100
    enabled: bool = True
    extra_config: Dict = {}


class ProviderUpdateRequest(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    dimension: Optional[int] = None
    api_style: Optional[str] = None
    description: Optional[str] = None
    price_info: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None
    provider_type: Optional[str] = None
    local_mode: Optional[str] = None
    category: Optional[str] = None
    extra_config: Optional[Dict] = None


class SetActiveRequest(BaseModel):
    provider_id: str
    category: str  # "llm" 或 "embedding"


class TestConnectionRequest(BaseModel):
    provider_id: str


# ==================== API 路由 ====================

@router.get("")
async def list_providers(category: str = None, enabled_only: bool = True):
    """
    列出所有模型提供者
    
    Query Params:
        category: 过滤类别 (llm / embedding)
        enabled_only: 是否只返回启用的
    """
    service = get_model_provider_service()
    providers = service.list_providers(category=category, enabled_only=enabled_only)
    
    # 分别获取活跃的提供者
    active_llm = service.get_active_provider_id('llm')
    active_embedding = service.get_active_provider_id('embedding')
    
    return {
        "providers": providers,
        "active_llm": active_llm,
        "active_embedding": active_embedding,
        "total": len(providers),
    }


@router.get("/llm")
async def list_llm_providers():
    """列出所有 LLM 提供者"""
    service = get_model_provider_service()
    providers = service.list_providers(category='llm')
    active = service.get_active_provider_id('llm')
    return {
        "providers": providers,
        "active_provider": active,
    }


@router.get("/embedding")
async def list_embedding_providers():
    """列出所有 Embedding 提供者"""
    service = get_model_provider_service()
    providers = service.list_providers(category='embedding')
    active = service.get_active_provider_id('embedding')
    return {
        "providers": providers,
        "active_provider": active,
    }


@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    """获取单个提供者详情"""
    service = get_model_provider_service()
    provider = service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"提供者不存在: {provider_id}")
    return provider


@router.post("")
async def create_provider(request: ProviderCreateRequest):
    """创建新的模型提供者"""
    service = get_model_provider_service()
    try:
        provider = service.create_provider(request.model_dump())
        return {"success": True, "provider": provider, "message": "模型提供者创建成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{provider_id}")
async def update_provider(provider_id: str, request: ProviderUpdateRequest):
    """更新模型提供者"""
    service = get_model_provider_service()
    
    # 只传递非 None 的字段
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    
    result = service.update_provider(provider_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail=f"提供者不存在: {provider_id}")
    
    return {"success": True, "provider": result, "message": "更新成功"}


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str):
    """删除模型提供者（系统预置的不可删除）"""
    service = get_model_provider_service()
    try:
        success = service.delete_provider(provider_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"提供者不存在: {provider_id}")
        return {"success": True, "message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/active/set")
async def set_active_provider(request: SetActiveRequest):
    """设置某类别的活跃提供者"""
    service = get_model_provider_service()
    try:
        service.set_active_provider(request.provider_id, request.category)
        return {
            "success": True,
            "message": f"已切换到 {request.provider_id}",
            "provider_id": request.provider_id,
            "category": request.category,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{provider_id}/toggle")
async def toggle_provider(provider_id: str, enabled: bool = True):
    """启用/禁用提供者"""
    service = get_model_provider_service()
    success = service.toggle_provider(provider_id, enabled)
    if not success:
        raise HTTPException(status_code=404, detail=f"提供者不存在: {provider_id}")
    return {"success": True, "message": f"{'启用' if enabled else '禁用'}成功"}


@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """测试模型连接"""
    service = get_model_provider_service()
    provider_data = service.get_provider(request.provider_id)
    if not provider_data:
        raise HTTPException(status_code=404, detail=f"提供者不存在: {request.provider_id}")
    
    config = service.get_provider_config(request.provider_id)
    category = provider_data['category']
    
    try:
        if category == 'llm':
            return await _test_llm_connection(config, provider_data)
        elif category == 'embedding':
            return await _test_embedding_connection(config, provider_data)
        else:
            return {"success": False, "error": f"未知类别: {category}"}
    except Exception as e:
        return {"success": False, "error": f"测试失败: {str(e)}"}


@router.post("/reset-defaults")
async def reset_defaults(category: str = None):
    """重置为默认配置"""
    service = get_model_provider_service()
    count = service.reset_to_defaults(category)
    return {"success": True, "message": f"已重置 {count} 个提供者配置", "reset_count": count}


# ==================== 内部辅助函数 ====================

async def _test_llm_connection(config: Dict, provider_data: Dict) -> Dict:
    """测试 LLM 连接"""
    import time
    
    provider_type = provider_data.get('provider_type', 'local')
    local_mode = provider_data.get('local_mode', '')
    
    try:
        from app.llm.providers.ollama import OllamaProvider
        from app.llm.providers.openai_compatible import OpenAICompatibleProvider
        from app.llm.providers.commercial import CommercialProvider
        from app.llm.providers.docker import DockerProvider
        
        # 根据类型创建 Provider 实例
        if provider_type == 'local' and local_mode == 'ollama':
            provider = OllamaProvider(config)
        elif provider_type == 'local' and local_mode == 'docker':
            provider = DockerProvider(config)
        elif provider_type == 'commercial':
            base_url = config.get('base_url', '').lower()
            if 'openai.com' in base_url or 'deepseek.com' in base_url or 'siliconflow' in base_url:
                provider = OpenAICompatibleProvider(config)
            else:
                provider = CommercialProvider(config)
        else:
            provider = OpenAICompatibleProvider(config)
        
        start = time.time()
        result = provider.test_connection()
        latency = int((time.time() - start) * 1000)
        result['latency_ms'] = latency
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_embedding_connection(config: Dict, provider_data: Dict) -> Dict:
    """测试 Embedding 连接"""
    import time
    import requests as http_requests
    
    base_url = config.get('base_url', '').rstrip('/')
    model = config.get('model', '')
    api_style = config.get('api_style', 'openai')
    api_key = config.get('api_key', '')
    timeout = config.get('timeout', 30)
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    test_text = "测试连接"
    start_time = time.time()
    
    try:
        if api_style == 'ollama':
            url = f"{base_url}/api/embed"
            payload = {"model": model, "input": [test_text]}
        else:
            url = f"{base_url}/embeddings"
            payload = {"model": model, "input": [test_text]}
        
        response = http_requests.post(url, json=payload, headers=headers, timeout=timeout)
        latency = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            embeddings = result.get("embeddings") or result.get("data", [])
            if embeddings:
                if isinstance(embeddings[0], list):
                    dim = len(embeddings[0])
                elif isinstance(embeddings[0], dict):
                    dim = len(embeddings[0].get("embedding", []))
                else:
                    dim = 0
                return {
                    "success": True,
                    "message": f"连接成功，向量维度: {dim}",
                    "latency_ms": latency,
                    "dimension": dim,
                }
            return {"success": False, "error": "返回数据格式异常", "latency_ms": latency}
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "latency_ms": latency,
            }
    except http_requests.exceptions.Timeout:
        return {"success": False, "error": "连接超时"}
    except http_requests.exceptions.ConnectionError:
        return {"success": False, "error": "无法连接到服务器"}
    except Exception as e:
        return {"success": False, "error": str(e)}
