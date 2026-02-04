# backend/app/llm/providers/commercial.py
"""
商用API提供者
用于调用各类商用大模型API

支持的服务:
- 智谱AI (GLM-4)
- 阿里云通义千问
- 百度文心一言
- 其他商用API
"""

import requests
from typing import Dict
from .base import BaseLLMProvider


class CommercialProvider(BaseLLMProvider):
    """
    商用API提供者
    
    特点:
    - 各厂商API格式可能略有不同
    - 需要API Key认证
    - 通常按调用量计费
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 识别具体的商用服务类型
        self.vendor = self._detect_vendor()
    
    def _detect_vendor(self) -> str:
        """根据base_url识别服务商"""
        url_lower = self.base_url.lower()
        if "bigmodel.cn" in url_lower or "zhipu" in url_lower:
            return "zhipu"
        elif "dashscope" in url_lower or "aliyun" in url_lower:
            return "aliyun"
        elif "baidu" in url_lower or "wenxin" in url_lower:
            return "baidu"
        elif "deepseek" in url_lower:
            return "deepseek"
        else:
            return "openai_compatible"
    
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用商用API进行对话
        自动适配不同服务商的API格式
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            模型返回的文本内容
        """
        if self.vendor == "zhipu":
            return self._chat_zhipu(system_prompt, user_prompt)
        elif self.vendor == "aliyun":
            return self._chat_aliyun(system_prompt, user_prompt)
        else:
            # 默认使用OpenAI兼容格式
            return self._chat_openai_compatible(system_prompt, user_prompt)
    
    def _chat_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        """OpenAI兼容格式调用"""
        base_url = self.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            if "/v1" not in base_url:
                base_url = f"{base_url}/v1"
        
        url = f"{base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                return self.extract_json(content)
            
            return "{}"
        except Exception as e:
            raise Exception(f"API调用失败: {e}")
    
    def _chat_zhipu(self, system_prompt: str, user_prompt: str) -> str:
        """智谱AI格式调用"""
        # 智谱使用标准OpenAI格式，但某些参数不同
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # 智谱部分模型支持response_format
        if "glm-4" in self.model.lower():
            payload["response_format"] = {"type": "json_object"}
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                return self.extract_json(content)
            
            return "{}"
        except Exception as e:
            raise Exception(f"智谱API调用失败: {e}")
    
    def _chat_aliyun(self, system_prompt: str, user_prompt: str) -> str:
        """阿里云通义千问格式调用"""
        # 通义千问使用OpenAI兼容格式
        base_url = self.base_url.rstrip("/")
        if "compatible-mode" not in base_url:
            base_url = f"{base_url}/compatible-mode/v1"
        
        url = f"{base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                return self.extract_json(content)
            
            return "{}"
        except Exception as e:
            raise Exception(f"通义千问API调用失败: {e}")
    
    def test_connection(self) -> Dict:
        """测试API连接"""
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "未配置API Key"
                }
            
            # 根据vendor选择测试方式
            if self.vendor == "zhipu":
                url = f"{self.base_url}/chat/completions"
            elif self.vendor == "aliyun":
                base_url = self.base_url.rstrip("/")
                if "compatible-mode" not in base_url:
                    url = f"{base_url}/compatible-mode/v1/chat/completions"
                else:
                    url = f"{base_url}/chat/completions"
            else:
                base_url = self.base_url.rstrip("/")
                if not base_url.endswith("/v1"):
                    if "/v1" not in base_url:
                        base_url = f"{base_url}/v1"
                url = f"{base_url}/chat/completions"
            
            response = requests.post(
                url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                },
                headers=self._get_headers(),
                timeout=15
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"{self.name}连接成功"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "API Key无效"
                }
            else:
                return {
                    "success": False,
                    "error": f"连接失败 ({response.status_code})"
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"无法连接服务({self.base_url})"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "连接超时"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
