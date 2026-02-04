# backend/app/core/llm_service.py
"""
LLM 服务模块
提供统一的大语言模型调用接口，支持多种提供者和模型
"""

import os
import json
import yaml
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
LLM_CONFIG_PATH = CONFIG_DIR / "llm_providers.yaml"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: str
    
    def to_dict(self) -> Dict:
        return {"role": self.role.value, "content": self.content}


@dataclass
class ChatCompletionConfig:
    """对话补全配置"""
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    response_format: Optional[Dict] = None  # {"type": "json_object"} for JSON mode
    stream: bool = False


@dataclass
class ChatCompletionResult:
    """对话补全结果"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: str = "stop"
    raw_response: Optional[Dict] = None


@dataclass
class ProviderConfig:
    """提供者配置"""
    id: str
    name: str
    type: str  # local or commercial
    base_url: str
    model: str
    api_key: str = ""
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 60
    description: str = ""
    price_per_1k_tokens: float = 0.0
    extra: Dict = field(default_factory=dict)


class LLMService:
    """
    LLM 服务类
    
    使用示例:
    ```python
    from app.core.llm_service import LLMService, Message, MessageRole
    
    # 创建服务实例
    llm = LLMService()
    
    # 简单对话
    result = await llm.chat("你好，请介绍一下自己")
    print(result.content)
    
    # 带系统提示的对话
    result = await llm.chat(
        "分析这句话的情感",
        system_prompt="你是一个情感分析专家"
    )
    
    # 使用指定提供者
    result = await llm.chat("测试", provider="openai")
    
    # JSON 模式
    result = await llm.chat_json(
        "提取这段话的关键信息",
        system_prompt="返回JSON格式"
    )
    ```
    """
    
    def __init__(self, config_path: Path = LLM_CONFIG_PATH):
        self.config_path = config_path
        self.providers: Dict[str, ProviderConfig] = {}
        self.active_provider: str = ""
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if not self.config_path.exists():
            print(f"⚠️ LLM配置文件不存在: {self.config_path}")
            self._use_default_config()
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            self.active_provider = config.get("active_provider", "local_qwen")
            
            # 加载所有提供者配置
            for key, value in config.items():
                if isinstance(value, dict) and "base_url" in value:
                    # 处理 API Key 环境变量
                    api_key = value.get("api_key", "")
                    if api_key and api_key.startswith("${") and api_key.endswith("}"):
                        env_var = api_key[2:-1]
                        api_key = os.environ.get(env_var, "")
                    
                    self.providers[key] = ProviderConfig(
                        id=key,
                        name=value.get("name", key),
                        type=value.get("type", "local"),
                        base_url=value.get("base_url", ""),
                        model=value.get("model", ""),
                        api_key=api_key,
                        max_tokens=value.get("max_tokens", 2000),
                        temperature=value.get("temperature", 0.7),
                        timeout=value.get("timeout", 60),
                        description=value.get("description", ""),
                        price_per_1k_tokens=value.get("price_per_1k_tokens", 0.0),
                    )
            
            print(f"✅ LLMService 配置加载成功，当前使用: {self.active_provider}")
        except Exception as e:
            print(f"⚠️ LLM配置加载失败: {e}")
            self._use_default_config()
    
    def _use_default_config(self):
        """使用默认配置"""
        self.active_provider = "local_qwen"
        self.providers = {
            "local_qwen": ProviderConfig(
                id="local_qwen",
                name="本地Qwen3",
                type="local",
                base_url="http://localhost:8001/v1",
                model="qwen3-chat",
                description="本地部署的Qwen3模型"
            )
        }
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
    
    def get_provider(self, name: str = None) -> ProviderConfig:
        """获取提供者配置"""
        provider_name = name or self.active_provider
        if provider_name not in self.providers:
            raise ValueError(f"未知的LLM提供者: {provider_name}")
        return self.providers[provider_name]
    
    def list_providers(self) -> List[Dict]:
        """列出所有可用的提供者"""
        return [
            {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "is_active": p.id == self.active_provider
            }
            for p in self.providers.values()
        ]
    
    async def chat(
        self,
        user_message: str,
        system_prompt: str = "",
        provider: str = None,
        config: ChatCompletionConfig = None
    ) -> ChatCompletionResult:
        """
        发送对话请求
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示（可选）
            provider: 提供者名称（可选，默认使用当前激活的提供者）
            config: 对话配置（可选）
        
        Returns:
            ChatCompletionResult: 对话结果
        """
        messages = []
        if system_prompt:
            messages.append(Message(MessageRole.SYSTEM, system_prompt))
        messages.append(Message(MessageRole.USER, user_message))
        
        return await self.chat_with_messages(messages, provider, config)
    
    async def chat_with_messages(
        self,
        messages: List[Message],
        provider: str = None,
        config: ChatCompletionConfig = None
    ) -> ChatCompletionResult:
        """
        使用消息列表发送对话请求
        
        Args:
            messages: 消息列表
            provider: 提供者名称
            config: 对话配置
        
        Returns:
            ChatCompletionResult: 对话结果
        """
        import httpx
        
        provider_config = self.get_provider(provider)
        chat_config = config or ChatCompletionConfig(
            temperature=provider_config.temperature,
            max_tokens=provider_config.max_tokens
        )
        
        headers = {"Content-Type": "application/json"}
        if provider_config.api_key:
            headers["Authorization"] = f"Bearer {provider_config.api_key}"
        
        url = f"{provider_config.base_url}/chat/completions"
        
        payload = {
            "model": provider_config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": chat_config.temperature,
            "max_tokens": chat_config.max_tokens,
            "top_p": chat_config.top_p,
            "frequency_penalty": chat_config.frequency_penalty,
            "presence_penalty": chat_config.presence_penalty,
        }
        
        if chat_config.response_format:
            payload["response_format"] = chat_config.response_format
        
        try:
            async with httpx.AsyncClient(timeout=provider_config.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                content = ""
                finish_reason = "stop"
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    message = choice.get("message", {})
                    content = message.get("content", "")
                    finish_reason = choice.get("finish_reason", "stop")
                
                return ChatCompletionResult(
                    content=content,
                    provider=provider_config.id,
                    model=provider_config.model,
                    usage=result.get("usage"),
                    finish_reason=finish_reason,
                    raw_response=result
                )
        except httpx.TimeoutException:
            raise TimeoutError(f"LLM请求超时 ({provider_config.timeout}秒)")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"LLM服务错误: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"LLM调用失败: {str(e)}")
    
    async def chat_json(
        self,
        user_message: str,
        system_prompt: str = "",
        provider: str = None,
        config: ChatCompletionConfig = None
    ) -> Dict:
        """
        发送对话请求并返回 JSON 格式结果
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示
            provider: 提供者名称
            config: 对话配置
        
        Returns:
            Dict: 解析后的 JSON 结果
        """
        chat_config = config or ChatCompletionConfig()
        chat_config.response_format = {"type": "json_object"}
        
        # 确保系统提示包含 JSON 指示
        if system_prompt and "json" not in system_prompt.lower():
            system_prompt += "\n请以 JSON 格式返回结果。"
        elif not system_prompt:
            system_prompt = "请以 JSON 格式返回结果。"
        
        result = await self.chat(user_message, system_prompt, provider, chat_config)
        
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', result.content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"无法解析 JSON 响应: {result.content[:200]}")
    
    async def test_connection(self, provider: str = None) -> Dict[str, Any]:
        """
        测试与 LLM 提供者的连接
        
        Args:
            provider: 提供者名称
        
        Returns:
            Dict: 测试结果
        """
        import httpx
        
        provider_config = self.get_provider(provider)
        
        headers = {"Content-Type": "application/json"}
        if provider_config.api_key:
            headers["Authorization"] = f"Bearer {provider_config.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 尝试获取模型列表
                models_url = f"{provider_config.base_url}/models"
                try:
                    response = await client.get(models_url, headers=headers)
                    if response.status_code == 200:
                        return {
                            "success": True,
                            "provider": provider_config.id,
                            "message": "连接成功",
                            "models": response.json().get("data", [])
                        }
                except:
                    pass
                
                # 尝试发送简单请求
                chat_url = f"{provider_config.base_url}/chat/completions"
                payload = {
                    "model": provider_config.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5
                }
                response = await client.post(chat_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider": provider_config.id,
                        "message": "连接成功"
                    }
                else:
                    return {
                        "success": False,
                        "provider": provider_config.id,
                        "message": f"连接失败: HTTP {response.status_code}"
                    }
        except httpx.TimeoutException:
            return {
                "success": False,
                "provider": provider_config.id,
                "message": "连接超时"
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider_config.id,
                "message": f"连接失败: {str(e)}"
            }


# 全局服务实例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取全局 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# 便捷函数
async def chat(
    user_message: str,
    system_prompt: str = "",
    provider: str = None
) -> str:
    """
    便捷的对话函数
    
    使用示例:
    ```python
    from app.core.llm_service import chat
    
    result = await chat("你好")
    print(result)
    ```
    """
    service = get_llm_service()
    result = await service.chat(user_message, system_prompt, provider)
    return result.content


async def chat_json(
    user_message: str,
    system_prompt: str = "",
    provider: str = None
) -> Dict:
    """
    便捷的 JSON 对话函数
    
    使用示例:
    ```python
    from app.core.llm_service import chat_json
    
    result = await chat_json(
        "分析这句话: 我很开心",
        system_prompt="返回情感分析结果"
    )
    print(result)  # {"emotion": "happy", "score": 0.9}
    ```
    """
    service = get_llm_service()
    return await service.chat_json(user_message, system_prompt, provider)
