# backend/app/api/llm.py
"""
LLM API 接口模块
提供大语言模型调用、配置管理等功能
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
LLM_CONFIG_PATH = CONFIG_DIR / "llm_providers.yaml"

router = APIRouter(prefix="/api/llm", tags=["LLM"])


# ==================== 数据模型 ====================

class ChatMessage(BaseModel):
    role: str  # system, user, assistant
    content: str

class ChatRequest(BaseModel):
    provider: str = ""  # 可选，不填则使用默认
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False

class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None

class ProviderInfo(BaseModel):
    id: str
    name: str
    type: str
    description: str
    is_active: bool

class TestConnectionRequest(BaseModel):
    provider: str


# ==================== LLM 客户端 ====================

class LLMClient:
    """统一的 LLM 调用客户端"""
    
    def __init__(self):
        self.providers: Dict[str, Dict] = {}
        self.active_provider: str = ""
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if not LLM_CONFIG_PATH.exists():
            self._use_default_config()
            return
        
        try:
            with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            self.active_provider = config.get("active_provider", "local_qwen")
            
            # 加载所有提供者配置
            for key, value in config.items():
                if isinstance(value, dict) and "base_url" in value:
                    self.providers[key] = value
            
            print(f"✅ LLM配置加载成功，当前使用: {self.active_provider}")
        except Exception as e:
            print(f"⚠️ LLM配置加载失败: {e}")
            self._use_default_config()
    
    def _use_default_config(self):
        """使用默认配置"""
        self.active_provider = "local_qwen"
        self.providers = {
            "local_qwen": {
                "name": "本地Qwen3",
                "type": "local",
                "base_url": "http://localhost:8001/v1",
                "model": "qwen3-chat",
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 60,
                "description": "本地部署的Qwen3模型"
            }
        }
    
    def reload_config(self):
        """重新加载配置"""
        self._load_config()
    
    def get_provider_config(self, provider_name: str = None) -> Dict:
        """获取提供者配置"""
        name = provider_name or self.active_provider
        if name not in self.providers:
            raise ValueError(f"未知的LLM提供者: {name}")
        
        config = self.providers[name].copy()
        
        # 处理环境变量中的 API Key
        api_key = config.get("api_key", "")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            config["api_key"] = os.environ.get(env_var, "")
        
        return config
    
    def list_providers(self) -> List[ProviderInfo]:
        """列出所有可用的提供者"""
        result = []
        for key, config in self.providers.items():
            result.append(ProviderInfo(
                id=key,
                name=config.get("name", key),
                type=config.get("type", "unknown"),
                description=config.get("description", ""),
                is_active=key == self.active_provider
            ))
        return result
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """调用 LLM 进行对话"""
        import httpx
        
        provider_name = request.provider or self.active_provider
        config = self.get_provider_config(provider_name)
        
        headers = {"Content-Type": "application/json"}
        api_key = config.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        url = f"{config['base_url']}/chat/completions"
        
        payload = {
            "model": config["model"],
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        
        timeout = config.get("timeout", 60)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                content = ""
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    content = message.get("content", "")
                
                usage = result.get("usage", None)
                
                return ChatResponse(
                    content=content,
                    provider=provider_name,
                    model=config["model"],
                    usage=usage
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"LLM请求超时 ({timeout}秒)")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"LLM服务错误: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")
    
    async def test_connection(self, provider_name: str) -> Dict[str, Any]:
        """测试与 LLM 提供者的连接"""
        import httpx
        
        config = self.get_provider_config(provider_name)
        
        headers = {"Content-Type": "application/json"}
        api_key = config.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 尝试调用 models 接口或发送简单请求
        url = f"{config['base_url']}/models"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider": provider_name,
                        "message": "连接成功",
                        "models": response.json().get("data", [])
                    }
                else:
                    # 尝试发送一个简单的 chat 请求
                    chat_url = f"{config['base_url']}/chat/completions"
                    payload = {
                        "model": config["model"],
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5
                    }
                    chat_response = await client.post(chat_url, json=payload, headers=headers)
                    if chat_response.status_code == 200:
                        return {
                            "success": True,
                            "provider": provider_name,
                            "message": "连接成功"
                        }
                    else:
                        return {
                            "success": False,
                            "provider": provider_name,
                            "message": f"连接失败: HTTP {chat_response.status_code}"
                        }
        except httpx.TimeoutException:
            return {
                "success": False,
                "provider": provider_name,
                "message": "连接超时"
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider_name,
                "message": f"连接失败: {str(e)}"
            }


# 全局客户端实例
llm_client = LLMClient()


# ==================== API 路由 ====================

@router.get("/providers")
async def get_providers():
    """获取所有可用的 LLM 提供者"""
    return {"providers": [p.dict() for p in llm_client.list_providers()]}


@router.post("/chat")
async def chat(request: ChatRequest):
    """调用 LLM 进行对话"""
    response = await llm_client.chat(request)
    return response.dict()


@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """测试 LLM 连接"""
    result = await llm_client.test_connection(request.provider)
    return result


@router.post("/reload-config")
async def reload_config():
    """重新加载 LLM 配置"""
    llm_client.reload_config()
    return {"success": True, "message": "配置已重新加载"}


@router.get("/active-provider")
async def get_active_provider():
    """获取当前激活的提供者"""
    return {
        "active_provider": llm_client.active_provider,
        "config": llm_client.get_provider_config()
    }


@router.put("/active-provider/{provider_name}")
async def set_active_provider(provider_name: str):
    """设置当前激活的提供者"""
    if provider_name not in llm_client.providers:
        raise HTTPException(status_code=404, detail=f"未知的提供者: {provider_name}")
    
    llm_client.active_provider = provider_name
    return {"success": True, "active_provider": provider_name}
