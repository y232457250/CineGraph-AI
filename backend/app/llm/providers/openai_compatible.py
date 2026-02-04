# backend/app/llm/providers/openai_compatible.py
"""
OpenAI兼容API提供者
用于调用OpenAI API或兼容OpenAI格式的第三方服务

支持的服务:
- OpenAI (GPT-4, GPT-4o, GPT-4o-mini等)
- DeepSeek
- 其他兼容OpenAI API格式的服务
"""

import requests
from typing import Dict
from .base import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    OpenAI兼容API提供者
    
    特点:
    - 使用标准OpenAI API格式
    - 支持 response_format 强制JSON输出
    - 需要API Key认证
    - 通常是商用付费服务
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 确保base_url格式正确
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        if not self.base_url.endswith("/v1"):
            # 检查是否已经包含完整路径
            if "/v1" not in self.base_url:
                self.base_url = f"{self.base_url}/v1"
    
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用OpenAI兼容API进行对话
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            模型返回的文本内容
        """
        url = f"{self.base_url}/chat/completions"
        
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
            
        except requests.exceptions.Timeout:
            raise Exception(f"API请求超时({self.timeout}秒)")
        except requests.exceptions.HTTPError as e:
            # 处理常见错误
            status_code = e.response.status_code
            if status_code == 401:
                raise Exception("API Key无效或已过期")
            elif status_code == 429:
                raise Exception("请求过于频繁，请稍后重试")
            elif status_code == 500:
                raise Exception("服务端错误，请稍后重试")
            else:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get("error", {}).get("message", str(e))
                    raise Exception(f"API请求失败: {error_msg}")
                except:
                    raise Exception(f"API请求失败: {e}")
        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {e}")
    
    def test_connection(self) -> Dict:
        """测试API连接"""
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "未配置API Key"
                }
            
            # 发送简单测试请求
            url = f"{self.base_url}/chat/completions"
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
                    "message": f"API连接成功，模型: {self.model}"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "API Key无效"
                }
            else:
                return {
                    "success": False,
                    "error": f"连接失败 ({response.status_code}): {response.text[:200]}"
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"无法连接API服务({self.base_url})"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "连接超时"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_models(self) -> list:
        """列出可用模型"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            models_data = response.json()
            if "data" in models_data:
                return [m.get("id", "") for m in models_data["data"]]
            return []
        except Exception:
            return []
