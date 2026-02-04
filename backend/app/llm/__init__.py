# backend/app/llm/__init__.py
"""
LLM提供者模块 - 统一管理各类大模型的调用

支持的模型类型:
- Ollama: 本地Ollama服务
- Docker: Docker容器部署的模型
- OpenAI: OpenAI兼容API (包括OpenAI、DeepSeek等)
- Commercial: 其他商用API (智谱、通义千问等)
"""

from .manager import LLMProviderManager
from .providers.base import BaseLLMProvider
from .providers.ollama import OllamaProvider
from .providers.docker import DockerProvider
from .providers.openai_compatible import OpenAICompatibleProvider
from .providers.commercial import CommercialProvider

__all__ = [
    "LLMProviderManager",
    "BaseLLMProvider",
    "OllamaProvider", 
    "DockerProvider",
    "OpenAICompatibleProvider",
    "CommercialProvider",
]
