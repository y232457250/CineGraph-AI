"""
统一配置管理
集中管理所有配置，支持 YAML/环境变量
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "local_ollama"
    base_url: str = "http://localhost:11434/v1"
    model: str = "qwen3:4b"
    api_key: str = ""
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 120


@dataclass
class EmbeddingConfig:
    """Embedding 配置"""
    provider: str = "local_ollama_embedding"
    base_url: str = "http://localhost:11434"
    model: str = "qwen3-embedding:4b-fp16"
    dimension: int = 1536
    timeout: int = 60


@dataclass
class AppConfig:
    """应用配置"""
    data_dir: Path = BASE_DIR / "data"
    chroma_db_path: Path = BASE_DIR / "data" / "chroma_db"
    annotations_dir: Path = BASE_DIR / "backend" / "data" / "annotations"
    media_index_path: Path = BASE_DIR / "data" / "media_index.json"
    ffmpeg_path: Optional[Path] = None


class Settings:
    """
    统一配置管理类
    
    优先级：环境变量 > 配置文件 > 默认值
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.llm = LLMConfig()
        self.embedding = EmbeddingConfig()
        self.app = AppConfig()
        
        self._load_llm_config()
        self._load_embedding_config()
        self._init_ffmpeg_path()
        
        self._initialized = True
    
    def _resolve_env_var(self, value: str) -> str:
        """解析环境变量 ${VAR} 语法"""
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, "")
        return value
    
    def _load_llm_config(self):
        """加载 LLM 配置"""
        llm_config_path = CONFIG_DIR / "llm_providers.yaml"
        if not llm_config_path.exists():
            return
        
        try:
            with open(llm_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            active_provider = config.get("active_provider", "local_ollama")
            provider_config = config.get(active_provider, {})
            
            self.llm.provider = active_provider
            self.llm.base_url = provider_config.get("base_url", self.llm.base_url)
            self.llm.model = provider_config.get("model", self.llm.model)
            self.llm.api_key = self._resolve_env_var(provider_config.get("api_key", ""))
            self.llm.max_tokens = provider_config.get("max_tokens", self.llm.max_tokens)
            self.llm.temperature = provider_config.get("temperature", self.llm.temperature)
            self.llm.timeout = provider_config.get("timeout", self.llm.timeout)
            
        except Exception as e:
            print(f"⚠️ 加载 LLM 配置失败: {e}")
    
    def _load_embedding_config(self):
        """加载 Embedding 配置"""
        embedding_config_path = CONFIG_DIR / "embedding_providers.yaml"
        if not embedding_config_path.exists():
            return
        
        try:
            with open(embedding_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            active_provider = config.get("active_provider", "local_ollama_embedding")
            provider_config = config.get(active_provider, {})
            
            self.embedding.provider = active_provider
            self.embedding.base_url = provider_config.get("base_url", self.embedding.base_url)
            self.embedding.model = provider_config.get("model", self.embedding.model)
            self.embedding.dimension = provider_config.get("dimension", self.embedding.dimension)
            self.embedding.timeout = provider_config.get("timeout", self.embedding.timeout)
            
        except Exception as e:
            print(f"⚠️ 加载 Embedding 配置失败: {e}")
    
    def _init_ffmpeg_path(self):
        """初始化 ffmpeg 路径"""
        ffmpeg_path = BASE_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
        if ffmpeg_path.exists():
            self.app.ffmpeg_path = ffmpeg_path
        else:
            self.app.ffmpeg_path = Path("ffmpeg")  # 使用系统 PATH
    
    def get_llm_provider_config(self, provider_id: str = None) -> Dict[str, Any]:
        """获取指定 LLM 提供者配置"""
        provider_id = provider_id or self.llm.provider
        llm_config_path = CONFIG_DIR / "llm_providers.yaml"
        
        if not llm_config_path.exists():
            return {}
        
        try:
            with open(llm_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config.get(provider_id, {})
        except Exception:
            return {}
    
    def reload(self):
        """重新加载所有配置"""
        self._initialized = False
        self.__init__()


# 全局配置实例
settings = Settings()


# 便捷函数
def get_settings() -> Settings:
    """获取配置实例"""
    return settings
