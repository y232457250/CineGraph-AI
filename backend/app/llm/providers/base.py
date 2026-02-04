# backend/app/llm/providers/base.py
"""
LLM提供者基类 - 定义统一接口
"""

import re
import json
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM配置数据类"""
    name: str
    type: str  # local, commercial
    local_mode: str  # ollama, docker, python
    base_url: str
    model: str
    api_key: str = ""
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 60
    description: str = ""
    price_per_1k_tokens: float = 0.0


class BaseLLMProvider(ABC):
    """
    LLM提供者基类
    所有具体的Provider都需要继承此类并实现chat方法
    """
    
    def __init__(self, config: Dict):
        """
        初始化Provider
        
        Args:
            config: 提供者配置字典
        """
        self.name = config.get("name", "Unknown")
        self.type = config.get("type", "local")
        self.local_mode = config.get("local_mode", "")
        self.base_url = config.get("base_url", "").rstrip("/")
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 60)
        self.description = config.get("description", "")
        
        # 处理API Key（支持环境变量）
        import os
        api_key = config.get("api_key", "")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            self.api_key = os.environ.get(env_var, "")
        else:
            self.api_key = api_key
    
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用LLM进行对话
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            模型返回的文本内容
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict:
        """
        测试连接是否正常
        
        Returns:
            {"success": bool, "message": str, "error": str}
        """
        pass
    
    def extract_json(self, text: str) -> str:
        """
        从响应文本中提取JSON部分
        处理模型可能返回的思考过程等非JSON内容
        支持提取JSON对象({...})或JSON数组([...])
        
        Args:
            text: 原始响应文本
            
        Returns:
            提取出的JSON字符串
        """
        if not text:
            return "{}"
        
        # 移除markdown代码块标记
        text = re.sub(r'```(?:json)?', '', text)
        text = re.sub(r'```', '', text)
        
        # 移除<think>...</think>标签（Qwen3等模型的思考过程）
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        text = text.strip()
        
        # 查找JSON对象和数组的起始位置
        obj_start = text.find('{')
        array_start = text.find('[')
        
        # 关键修复：只有当数组在对象之前开始（或没有对象）时，才认为是顶层数组
        # 如果数组在对象内部（如 {"can_follow": ["答句"]}），应该提取整个对象
        
        if obj_start != -1:
            obj_end = text.rfind('}')
            if obj_end > obj_start:
                # 检查是否有顶层数组（在对象之前开始）
                if array_start != -1 and array_start < obj_start:
                    # 数组在对象之前，是顶层数组
                    array_end = text.rfind(']')
                    if array_end > array_start:
                        return text[array_start:array_end + 1].strip()
                # 否则返回JSON对象
                return text[obj_start:obj_end + 1].strip()
        
        # 没有对象，尝试提取数组
        if array_start != -1:
            array_end = text.rfind(']')
            if array_end > array_start:
                return text[array_start:array_end + 1].strip()
        
        return "{}"
    
    def parse_json_response(self, text: str) -> Dict:
        """
        解析JSON响应
        
        Args:
            text: 响应文本
            
        Returns:
            解析后的字典，失败返回空字典
        """
        try:
            json_str = self.extract_json(text)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            print(f"   原始文本前200字符: {text[:200] if text else '(空)'}")
            return {}
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} model={self.model}>"
