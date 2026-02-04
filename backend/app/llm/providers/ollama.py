# backend/app/llm/providers/ollama.py
"""
Ollama LLM提供者
用于调用本地Ollama服务运行的模型

Ollama API特点:
1. 使用 /api/generate 或 /api/chat 端点
2. 不支持 response_format 参数强制JSON输出
3. 需要在提示词中明确要求JSON格式
4. 响应格式与OpenAI不同
"""

import requests
from typing import Dict
from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    Ollama本地模型提供者
    
    特点:
    - 使用Ollama原生API (/api/generate 或 /api/chat)
    - 需要通过提示词约束JSON输出
    - 支持流式和非流式响应
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # Ollama base_url 通常是 http://localhost:11434
        # 如果配置的是 /v1 结尾，需要去掉
        if self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3]
    
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        调用Ollama进行对话
        使用 /api/chat 端点
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            模型返回的文本内容
        """
        url = f"{self.base_url}/api/chat"
        
        # 强调JSON格式要求
        enhanced_system = f"{system_prompt}\n\n请严格按照JSON格式输出，不要输出任何其他内容。"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
            # Ollama 0.5+ 支持 format 参数强制JSON输出
            "format": "json",
            # 禁用Qwen3等模型的思考模式，直接输出结果
            "think": False
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Ollama chat 响应格式: {"message": {"content": "...", "thinking": "..."}}
            content = ""
            if "message" in result:
                content = result["message"].get("content", "")
                
                # 如果content为空但有thinking，尝试从thinking中提取JSON
                if not content and result["message"].get("thinking"):
                    thinking = result["message"]["thinking"]
                    json_match = self._extract_json_from_thinking(thinking)
                    if json_match:
                        content = json_match
                    else:
                        print(f"⚠️ Ollama返回空content，thinking中未找到有效JSON")
                        
            # 兼容 generate 响应格式
            elif "response" in result:
                content = result["response"]
            
            if not content:
                print(f"⚠️ Ollama返回空内容")
                return "{}"
            
            # 提取JSON（处理可能的思考过程）
            return self.extract_json(content)
            
        except requests.exceptions.Timeout:
            raise Exception(f"Ollama请求超时({self.timeout}秒)，请检查模型是否正在加载")
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接Ollama服务({self.base_url})，请确认服务已启动")
        except Exception as e:
            raise Exception(f"Ollama调用失败: {e}")
    
    def _extract_json_from_thinking(self, thinking: str) -> str:
        """
        从thinking字段中提取JSON
        Qwen3等模型有时会在thinking的最后部分包含JSON输出
        """
        import re
        
        # 尝试找到thinking中的JSON块
        # 查找最后一个完整的JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, thinking, re.DOTALL)
        
        if matches:
            # 返回最后一个匹配（通常是最终输出）
            for match in reversed(matches):
                try:
                    import json
                    json.loads(match)  # 验证是否是有效JSON
                    return match
                except:
                    continue
        
        return ""
    
    def generate(self, prompt: str) -> str:
        """
        使用generate端点（单轮对话）
        某些场景下比chat更快
        
        Args:
            prompt: 完整提示词
            
        Returns:
            模型返回的文本
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "")
            return self.extract_json(content)
        except Exception as e:
            raise Exception(f"Ollama generate调用失败: {e}")
    
    def test_connection(self) -> Dict:
        """测试Ollama连接"""
        try:
            # 先检查服务是否在线
            tags_url = f"{self.base_url}/api/tags"
            response = requests.get(tags_url, timeout=5)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # 检查目标模型是否存在 - 使用精确匹配或标签匹配
            # 支持格式: "qwen3:4b" 匹配 "qwen3:4b" 或 "qwen3:latest"（如果self.model是"qwen3"）
            target_model = self.model.lower().strip()
            model_found = False
            for name in model_names:
                name_lower = name.lower().strip()
                # 精确匹配
                if target_model == name_lower:
                    model_found = True
                    break
                # 匹配不带标签的模型名（如 "qwen3" 匹配 "qwen3:latest"）
                if ':' not in target_model and name_lower.startswith(target_model + ':'):
                    model_found = True
                    break
                # 匹配带标签的模型（如 "qwen3:4b" 匹配 "qwen3:4b"）
                if ':' in target_model:
                    base_name = target_model.split(':')[0]
                    tag = target_model.split(':')[1]
                    if name_lower.startswith(base_name + ':') and tag in name_lower:
                        model_found = True
                        break
            
            if model_found:
                # 简单测试生成
                test_url = f"{self.base_url}/api/generate"
                test_response = requests.post(
                    test_url,
                    json={
                        "model": self.model,
                        "prompt": "Say 'OK'",
                        "stream": False,
                        "options": {"num_predict": 5}
                    },
                    timeout=30
                )
                test_response.raise_for_status()
                return {
                    "success": True, 
                    "message": f"Ollama连接成功，模型 {self.model} 可用"
                }
            else:
                return {
                    "success": False,
                    "error": f"模型 {self.model} 未找到，可用模型: {', '.join(model_names[:5])}"
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"无法连接Ollama服务({self.base_url})，请确认服务已启动"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "连接超时，模型可能正在加载中"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_models(self) -> list:
        """列出Ollama中可用的模型"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m.get("name", "") for m in models]
        except Exception:
            return []
