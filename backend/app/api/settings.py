# backend/app/api/settings.py
"""
统一设置 API 接口模块
提供应用程序所有配置的管理功能
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
BACKEND_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
LLM_CONFIG_PATH = CONFIG_DIR / "llm_providers.yaml"
EMBEDDING_CONFIG_PATH = CONFIG_DIR / "embedding_providers.yaml"
THEME_CONFIG_PATH = CONFIG_DIR / "theme_config.json"
PROMPT_CONFIG_PATH = CONFIG_DIR / "prompt_config.json"
SETTINGS_PATH = BACKEND_CONFIG_DIR / "settings.yaml"

router = APIRouter(prefix="/api/settings", tags=["Settings"])


# ==================== 数据模型 ====================

class AnnotationSettings(BaseModel):
    batch_size: int = 10
    max_retries: int = 3
    retry_delay: int = 1000
    save_interval: int = 5
    concurrent_requests: int = 1


class VectorizationSettings(BaseModel):
    batch_size: int = 50
    max_retries: int = 3
    retry_delay: int = 500
    concurrent_requests: int = 2


class VectorDBSettings(BaseModel):
    type: str = "chroma"
    path: str = "data/chroma_db"
    collection_name: str = "cinegraph_subtitles"


class PathSettings(BaseModel):
    media_root: str = "D:\\AI\\CineGraph-AI\\data\\media"
    annotations_dir: str = "data/annotations"
    vectors_dir: str = "data/chroma_db"
    cache_dir: str = "data/cache"
    posters_dir: str = "data/posters"


class AppSettings(BaseModel):
    theme: str = "dark"
    language: str = "zh-CN"
    auto_save: bool = True
    confirm_before_delete: bool = True
    show_tips: bool = True


class AllSettings(BaseModel):
    annotation: AnnotationSettings = AnnotationSettings()
    vectorization: VectorizationSettings = VectorizationSettings()
    vector_db: VectorDBSettings = VectorDBSettings()
    paths: PathSettings = PathSettings()
    app: AppSettings = AppSettings()


class SettingsUpdate(BaseModel):
    section: str  # "annotation", "vectorization", "vector_db", "paths", "app"
    data: Dict[str, Any]


# ==================== 辅助函数 ====================

def load_settings() -> Dict[str, Any]:
    """加载所有设置"""
    default_settings = AllSettings().model_dump()
    
    if not SETTINGS_PATH.exists():
        return default_settings
    
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            saved_settings = yaml.safe_load(f) or {}
        
        # 合并默认设置和保存的设置
        for key in default_settings:
            if key in saved_settings:
                if isinstance(default_settings[key], dict):
                    default_settings[key].update(saved_settings[key])
                else:
                    default_settings[key] = saved_settings[key]
        
        return default_settings
    except Exception as e:
        print(f"⚠️ 加载设置失败: {e}")
        return default_settings


def save_settings(settings: Dict[str, Any]) -> bool:
    """保存设置"""
    try:
        BACKEND_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        print(f"⚠️ 保存设置失败: {e}")
        return False


# ==================== API 路由 ====================

@router.get("")
async def get_all_settings():
    """获取所有设置"""
    return load_settings()


@router.get("/{section}")
async def get_settings_section(section: str):
    """获取指定部分的设置"""
    settings = load_settings()
    
    if section not in settings:
        raise HTTPException(status_code=404, detail=f"设置部分 '{section}' 不存在")
    
    return settings[section]


@router.put("/{section}")
async def update_settings_section(section: str, data: Dict[str, Any]):
    """更新指定部分的设置"""
    settings = load_settings()
    
    if section not in settings:
        raise HTTPException(status_code=404, detail=f"设置部分 '{section}' 不存在")
    
    # 更新设置
    if isinstance(settings[section], dict):
        settings[section].update(data)
    else:
        settings[section] = data
    
    # 保存
    if save_settings(settings):
        return {"success": True, "message": "设置已保存"}
    else:
        raise HTTPException(status_code=500, detail="保存设置失败")


@router.post("/reset")
async def reset_settings():
    """重置所有设置为默认值"""
    default_settings = AllSettings().model_dump()
    
    if save_settings(default_settings):
        return {"success": True, "message": "设置已重置为默认值"}
    else:
        raise HTTPException(status_code=500, detail="重置设置失败")


@router.get("/system/info")
async def get_system_info():
    """获取系统信息"""
    import platform
    import sys
    
    return {
        "app_name": "CineGraph-AI",
        "app_version": "1.0.0-beta",
        "python_version": sys.version,
        "platform": platform.system(),
        "platform_version": platform.version(),
        "config_dir": str(CONFIG_DIR),
        "backend_config_dir": str(BACKEND_CONFIG_DIR),
    }


@router.get("/llm/summary")
async def get_llm_summary():
    """获取 LLM 配置摘要（不包含 API Key）"""
    if not LLM_CONFIG_PATH.exists():
        return {"providers": [], "active_provider": None}
    
    try:
        with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        active_provider = config.get("active_provider", "")
        providers = []
        
        for key, value in config.items():
            if isinstance(value, dict) and "base_url" in value:
                providers.append({
                    "id": key,
                    "name": value.get("name", key),
                    "type": value.get("type", "unknown"),
                    "local_mode": value.get("local_mode", ""),
                    "model": value.get("model", ""),
                    "description": value.get("description", ""),
                    "is_active": key == active_provider,
                    "has_api_key": bool(value.get("api_key")),
                    "price_per_1k_tokens": value.get("price_per_1k_tokens", 0),
                })
        
        return {
            "providers": providers,
            "active_provider": active_provider,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取 LLM 配置失败: {str(e)}")


@router.put("/llm/active")
async def set_active_llm_provider(provider_id: str):
    """设置当前激活的 LLM 提供者"""
    if not LLM_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="LLM 配置文件不存在")
    
    try:
        with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 检查提供者是否存在
        if provider_id not in config or not isinstance(config[provider_id], dict):
            raise HTTPException(status_code=404, detail=f"提供者 '{provider_id}' 不存在")
        
        # 更新激活的提供者
        config["active_provider"] = provider_id
        
        # 保存
        with open(LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        
        # 重新加载 LLM 客户端
        try:
            from app.api.llm import llm_client
            llm_client.reload_config()
        except Exception as e:
            print(f"⚠️ 重新加载 LLM 配置失败: {e}")
        
        return {"success": True, "message": f"已切换到 {provider_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/embedding/summary")
async def get_embedding_summary():
    """获取 Embedding 配置摘要"""
    if not EMBEDDING_CONFIG_PATH.exists():
        return {"providers": [], "active_provider": None}
    
    try:
        with open(EMBEDDING_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        active_provider = config.get("active_provider", "")
        providers = []
        
        for key, value in config.items():
            if isinstance(value, dict) and "base_url" in value:
                providers.append({
                    "id": key,
                    "name": value.get("name", key),
                    "type": value.get("type", "unknown"),
                    "local_mode": value.get("local_mode", ""),
                    "model": value.get("model", ""),
                    "dimension": value.get("dimension", 0),
                    "description": value.get("description", ""),
                    "price_per_1k_tokens": value.get("price_per_1k_tokens", 0),
                    "is_active": key == active_provider,
                })
        
        return {
            "providers": providers,
            "active_provider": active_provider,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取 Embedding 配置失败: {str(e)}")


@router.put("/embedding/active")
async def set_active_embedding_provider(provider_id: str):
    """设置当前激活的 Embedding 提供者"""
    if not EMBEDDING_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    
    try:
        with open(EMBEDDING_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 检查提供者是否存在
        if provider_id not in config or not isinstance(config[provider_id], dict):
            raise HTTPException(status_code=404, detail=f"Embedding 提供者 '{provider_id}' 不存在")
        
        # 更新激活的提供者
        config["active_provider"] = provider_id
        
        # 保存
        with open(EMBEDDING_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        
        return {"success": True, "message": f"已切换 Embedding 到 {provider_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/embedding/test-connection")
async def test_embedding_connection(request: Dict[str, Any]):
    """测试 Embedding 模型连接"""
    provider_id = request.get("provider_id", "")
    
    if not provider_id:
        raise HTTPException(status_code=400, detail="缺少 provider_id 参数")
    
    if not EMBEDDING_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    
    try:
        import time
        import requests as http_requests
        
        with open(EMBEDDING_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        if provider_id not in config or not isinstance(config[provider_id], dict):
            raise HTTPException(status_code=404, detail=f"Embedding 提供者 '{provider_id}' 不存在")
        
        provider_config = config[provider_id]
        base_url = provider_config.get("base_url", "").rstrip("/")
        model = provider_config.get("model", "")
        api_style = provider_config.get("api_style", "openai")
        timeout = provider_config.get("timeout", 30)
        
        # 处理 API Key
        api_key = provider_config.get("api_key", "")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            import os
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, "")
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 根据 API 风格构造请求
        test_text = "测试连接"
        start_time = time.time()
        
        if api_style == "ollama":
            url = f"{base_url}/embed" if base_url.endswith("/api") else f"{base_url}/api/embed"
            payload = {"model": model, "input": [test_text]}
        else:
            url = f"{base_url}/embeddings"
            payload = {"model": model, "input": [test_text]}
        
        response = http_requests.post(url, json=payload, headers=headers, timeout=timeout)
        elapsed = round((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            # 验证返回格式
            embeddings = result.get("embeddings") or result.get("data", [])
            if embeddings:
                dimension = len(embeddings[0]) if isinstance(embeddings[0], list) else len(embeddings[0].get("embedding", []))
                return {
                    "success": True,
                    "message": f"连接成功，向量维度: {dimension}",
                    "latency_ms": elapsed,
                    "dimension": dimension,
                    "model": model
                }
            else:
                return {
                    "success": False,
                    "message": "返回数据格式异常",
                    "latency_ms": elapsed
                }
        else:
            return {
                "success": False,
                "message": f"请求失败: HTTP {response.status_code}",
                "error": response.text[:200] if response.text else "未知错误"
            }
    except http_requests.exceptions.Timeout:
        return {"success": False, "message": "连接超时"}
    except http_requests.exceptions.ConnectionError:
        return {"success": False, "message": "无法连接到服务器，请检查服务是否启动"}
    except Exception as e:
        return {"success": False, "message": f"测试失败: {str(e)}"}


@router.get("/vectordb/stats")
async def get_vectordb_stats():
    """获取向量数据库统计信息"""
    settings = load_settings()
    vector_path = Path(settings["paths"]["vectors_dir"])
    
    stats = {
        "type": settings["vector_db"]["type"],
        "path": str(vector_path),
        "collection_name": settings["vector_db"]["collection_name"],
        "total_vectors": 0,
        "total_movies": 0,
        "storage_size_mb": 0,
    }
    
    # 尝试获取实际统计
    if vector_path.exists():
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(vector_path))
            collection = client.get_or_create_collection(settings["vector_db"]["collection_name"])
            stats["total_vectors"] = collection.count()
            
            # 计算存储大小
            total_size = sum(f.stat().st_size for f in vector_path.rglob("*") if f.is_file())
            stats["storage_size_mb"] = round(total_size / (1024 * 1024), 2)
        except Exception as e:
            print(f"⚠️ 获取向量库统计失败: {e}")
    
    return stats
