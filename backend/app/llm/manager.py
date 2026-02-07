# backend/app/llm/manager.py
"""
LLM提供者管理器
统一管理和调度各类LLM提供者
优先从数据库读取配置，回退到YAML文件
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from .providers.base import BaseLLMProvider
from .providers.ollama import OllamaProvider
from .providers.docker import DockerProvider
from .providers.openai_compatible import OpenAICompatibleProvider
from .providers.commercial import CommercialProvider


# 配置文件路径（作为回退）
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
LLM_CONFIG_PATH = CONFIG_DIR / "llm_providers.yaml"


class LLMProviderManager:
    """
    LLM提供者管理器
    
    功能:
    - 优先从数据库加载模型配置
    - 回退到YAML配置文件
    - 根据配置类型创建对应的Provider实例
    - 切换活跃的Provider
    - 列出所有可用的Provider
    """
    
    def __init__(self, config_path: Path = LLM_CONFIG_PATH):
        self.config_path = config_path
        self.providers: Dict[str, Dict] = {}
        self.active_provider: str = ""
        self._provider_cache: Dict[str, BaseLLMProvider] = {}
        self._use_db = False
        self._load_config()
    
    def _load_config(self):
        """加载配置 - 优先数据库，回退YAML"""
        try:
            self._load_from_db()
            if self.providers:
                self._use_db = True
                return
        except Exception as e:
            print(f"⚠️ 从数据库加载LLM配置失败，回退到YAML: {e}")
        
        self._load_from_yaml()
    
    def _load_from_db(self):
        """从数据库加载配置"""
        from app.core.model_provider_service import get_model_provider_service
        service = get_model_provider_service()
        
        providers_list = service.list_providers(category='llm')
        if not providers_list:
            return
        
        self.providers = {}
        for p in providers_list:
            provider_id = p['id']
            # 获取完整配置（含API Key）
            config = service.get_provider_config(provider_id)
            if config:
                self.providers[provider_id] = config
                if p.get('is_active'):
                    self.active_provider = provider_id
        
        if not self.active_provider and self.providers:
            self.active_provider = next(iter(self.providers))
        
        print(f"✅ LLM配置从数据库加载成功，当前使用: {self.active_provider} ({len(self.providers)} 个提供者)")
    
    def _load_from_yaml(self):
        """从YAML文件加载配置（回退方案）"""
        if not self.config_path.exists():
            print(f"⚠️ LLM配置文件不存在: {self.config_path}")
            self._use_default_config()
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            self.active_provider = config.get("active_provider", "local_ollama")
            
            for key, value in config.items():
                if isinstance(value, dict) and "base_url" in value:
                    self.providers[key] = value
            
            print(f"✅ LLM配置从YAML加载成功，当前使用: {self.active_provider}")
        except Exception as e:
            print(f"⚠️ LLM配置加载失败: {e}")
            self._use_default_config()
    
    def _use_default_config(self):
        """使用默认配置"""
        self.active_provider = "local_ollama"
        self.providers = {
            "local_ollama": {
                "name": "本地Ollama",
                "type": "local",
                "local_mode": "ollama",
                "base_url": "http://localhost:11434/v1",
                "model": "qwen3:4b",
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 120,
                "description": "通过Ollama运行的本地模型"
            }
        }
    
    def _create_provider(self, provider_id: str, config: Dict) -> BaseLLMProvider:
        """
        根据配置创建对应的Provider实例
        
        Args:
            provider_id: 提供者ID
            config: 提供者配置
            
        Returns:
            Provider实例
        """
        provider_type = config.get("type", "local")
        local_mode = config.get("local_mode", "")
        
        # 根据类型选择Provider
        if provider_type == "local":
            if local_mode == "ollama":
                return OllamaProvider(config)
            elif local_mode == "docker":
                return DockerProvider(config)
            else:
                # 默认使用Docker Provider（兼容OpenAI格式）
                return DockerProvider(config)
        elif provider_type == "commercial":
            # 检查是否是OpenAI或DeepSeek（使用标准格式）
            base_url = config.get("base_url", "").lower()
            if "openai.com" in base_url or "deepseek.com" in base_url:
                return OpenAICompatibleProvider(config)
            else:
                return CommercialProvider(config)
        else:
            # 未知类型，尝试使用OpenAI兼容格式
            return OpenAICompatibleProvider(config)
    
    def get_provider(self, provider_id: str = None) -> BaseLLMProvider:
        """
        获取LLM提供者实例
        
        Args:
            provider_id: 提供者ID，为空则使用当前活跃的提供者
            
        Returns:
            Provider实例
        """
        provider_id = provider_id or self.active_provider
        
        if provider_id not in self.providers:
            raise ValueError(f"未知的LLM提供者: {provider_id}")
        
        # 使用缓存
        if provider_id not in self._provider_cache:
            config = self.providers[provider_id]
            self._provider_cache[provider_id] = self._create_provider(provider_id, config)
        
        return self._provider_cache[provider_id]
    
    def list_providers(self) -> List[Dict]:
        """
        列出所有可用的提供者
        
        Returns:
            提供者信息列表
        """
        result = []
        for key, config in self.providers.items():
            result.append({
                "id": key,
                "name": config.get("name", key),
                "type": config.get("type", "unknown"),
                "local_mode": config.get("local_mode", ""),
                "description": config.get("description", ""),
                "is_active": key == self.active_provider,
                "price_per_1k_tokens": config.get("price_per_1k_tokens", 0),
                "model": config.get("model", ""),
                "base_url": config.get("base_url", ""),
            })
        return result
    
    def set_active_provider(self, provider_id: str):
        """
        设置当前活跃的提供者
        
        Args:
            provider_id: 提供者ID
        """
        if provider_id not in self.providers:
            raise ValueError(f"未知的LLM提供者: {provider_id}")
        
        self.active_provider = provider_id
        
        # 同步到数据库
        if self._use_db:
            try:
                from app.core.model_provider_service import get_model_provider_service
                service = get_model_provider_service()
                service.set_active_provider(provider_id, 'llm')
            except Exception as e:
                print(f"⚠️ 同步活跃提供者到数据库失败: {e}")
        
        print(f"✅ 已切换LLM提供者: {provider_id}")
    
    def test_provider(self, provider_id: str = None) -> Dict:
        """
        测试提供者连接
        
        Args:
            provider_id: 提供者ID，为空则测试当前活跃的提供者
            
        Returns:
            测试结果
        """
        try:
            provider = self.get_provider(provider_id)
            return provider.test_connection()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_provider_info(self, provider_id: str = None) -> Dict:
        """
        获取提供者详细信息
        
        Args:
            provider_id: 提供者ID
            
        Returns:
            提供者配置信息
        """
        provider_id = provider_id or self.active_provider
        
        if provider_id not in self.providers:
            return {}
        
        config = self.providers[provider_id].copy()
        config["id"] = provider_id
        config["is_active"] = provider_id == self.active_provider
        
        # 隐藏API Key
        if "api_key" in config and config["api_key"]:
            config["api_key"] = "***" + config["api_key"][-4:] if len(config["api_key"]) > 4 else "***"
        
        return config
    
    def reload_config(self):
        """重新加载配置"""
        self._provider_cache.clear()
        self._load_config()
