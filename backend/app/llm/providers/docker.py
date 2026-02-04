# backend/app/llm/providers/docker.py
"""
Docker容器部署的LLM提供者
用于调用通过Docker部署的本地模型（如vLLM、TGI等）

Docker部署的模型通常兼容OpenAI API格式，支持:
1. /v1/chat/completions 端点
2. response_format 参数强制JSON输出
3. 标准的OpenAI响应格式
"""

import requests
from typing import Dict
from .base import BaseLLMProvider


class DockerProvider(BaseLLMProvider):
    """
    Docker容器部署模型提供者
    
    支持的部署方式:
    - vLLM
    - Text Generation Inference (TGI)
    - LocalAI
    - 其他兼容OpenAI API的容器
    
    特点:
    - 使用OpenAI兼容API格式
    - 支持 response_format 强制JSON输出
    - 通常运行在本地端口(如8001)
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 确保base_url以/v1结尾
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"
    
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用Docker部署的模型进行对话
        使用OpenAI兼容的chat/completions端点
        
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
            
            # OpenAI格式响应
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                # 提取JSON（处理可能的额外内容）
                return self.extract_json(content)
            
            return "{}"
            
        except requests.exceptions.Timeout:
            raise Exception(f"Docker模型请求超时({self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接Docker模型服务({self.base_url})，请确认容器已启动")
        except requests.exceptions.HTTPError as e:
            # 尝试获取详细错误信息
            try:
                error_detail = e.response.json()
                raise Exception(f"Docker模型请求失败: {error_detail}")
            except:
                raise Exception(f"Docker模型请求失败: {e}")
        except Exception as e:
            raise Exception(f"Docker模型调用失败: {e}")
    
    def completions(self, prompt: str) -> str:
        """
        使用completions端点（某些模型可能只支持这个）
        
        Args:
            prompt: 完整提示词
            
        Returns:
            模型返回的文本
        """
        url = f"{self.base_url}/completions"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
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
                content = result["choices"][0].get("text", "")
                return self.extract_json(content)
            
            return "{}"
        except Exception as e:
            raise Exception(f"Docker completions调用失败: {e}")
    
    def test_connection(self) -> Dict:
        """测试Docker模型连接"""
        try:
            # 先检查模型列表端点
            models_url = f"{self.base_url}/models"
            response = requests.get(models_url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = []
                if "data" in models_data:
                    available_models = [m.get("id", "") for m in models_data["data"]]
                
                # 简单测试chat
                test_url = f"{self.base_url}/chat/completions"
                test_response = requests.post(
                    test_url,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 5
                    },
                    headers=self._get_headers(),
                    timeout=30
                )
                
                if test_response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Docker模型连接成功，模型: {self.model}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"模型测试失败: {test_response.text[:200]}"
                    }
            else:
                # 某些部署可能不支持/models端点，直接测试chat
                test_url = f"{self.base_url}/chat/completions"
                test_response = requests.post(
                    test_url,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 5
                    },
                    headers=self._get_headers(),
                    timeout=30
                )
                
                if test_response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Docker模型连接成功"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"连接失败: {test_response.text[:200]}"
                    }
                    
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"无法连接Docker服务({self.base_url})，请确认容器已启动"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "连接超时，模型可能正在加载中"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}
