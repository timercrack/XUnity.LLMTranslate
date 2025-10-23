"""
API客户端模块，负责与大模型API通信
"""

import json
import re
import requests
from typing import Dict, Any, List, Optional
from core.character_limiter import normalize_text as limit_characters

class APIClient:
    """API客户端类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化API客户端
        
        Args:
            config: 配置信息
        """
        self.config = config
    def _log(self, message: str):
        print(f"[api] {message}")

    def _build_common_payload(self):
        api_url = self.config.get("api_url")
        api_key = self.config.get("api_key")
        model_name = self.config.get("model_name")
        system_prompt = self.config.get("system_prompt")

        if not api_url or not api_key or not model_name:
            self._log("错误: API配置不完整，请检查API URL、API Key和模型名称")
            return None, {"success": False, "text": "翻译失败: API配置不完整"}

        try:
            temperature = float(self.config.get("temperature", 1.0))
        except (ValueError, TypeError):
            temperature = 1.0

        try:
            max_tokens = int(self.config.get("max_tokens", 8192))
            max_tokens = max(1, max_tokens)
        except (ValueError, TypeError):
            max_tokens = 8192

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        return {
            "api_url": api_url,
            "model_name": model_name,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "headers": headers
        }, None
    
    def translate_batch(self, texts: List[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not texts:
            return {"success": True, "translations": []}

        common, error = self._build_common_payload()
        if error:
            return error

        if not common:
            return {"success": False, "text": "翻译失败: API配置不完整"}

        api_url = common["api_url"]
        model_name = common["model_name"]
        system_prompt = (common.get("system_prompt") or "").strip()
        temperature = common["temperature"]
        max_tokens = common["max_tokens"]
        headers = common["headers"]

        user_message = json.dumps(texts, ensure_ascii=False)

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        messages.append({
            "role": "user",
            "content": user_message
        })

        data = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        # print("批量请求消息体", messages)
        # print(">>>>>>>>>>", sanitized_texts)

        try:
            response = requests.post(api_url, headers=headers, json=data, timeout=180)
        except requests.exceptions.Timeout:
            self._log("错误: 批量API请求超时")
            return {"success": False, "text": "翻译失败: API请求超时"}
        except requests.exceptions.ConnectionError:
            self._log("错误: 无法连接到API服务器（批量请求）")
            return {"success": False, "text": "翻译失败: 无法连接到API服务器"}
        except Exception as e:
            self._log(f"批量API请求发生错误: {str(e)}")
            return {"success": False, "text": f"翻译失败: {str(e)}"}

        if response.status_code != 200:
            self._log(f"批量API请求失败，状态码: {response.status_code}")
            self._log(f"批量API错误响应: {response.text}")
            return {"success": False, "text": f"翻译失败: API返回错误码 {response.status_code}"}

        response_data = {}
        try:
            response_data = response.json()
            # self._log(f"批量API原始响应: {response.text}")
        except ValueError as e:
            self._log(f"批量API响应解析失败: {str(e)}")
            self._log(f"批量API响应文本: {response.text}")
            return {"success": False, "text": "翻译失败: 无法解析API响应"}

        try:
            raw_content = response_data["choices"][0]["message"]["content"]
            usage = response_data.get("usage", {})

            translations = self._extract_batch_translations(raw_content, len(texts))
            if not translations:
                self._log(f"批量翻译解析失败: 无法提取翻译结果，批量翻译原始内容: {raw_content}")
                return {"success": False, "text": "翻译失败: 无法解析批量翻译结果"}
            else:
                self._log(f"批量翻译解析结果: {translations}")

            restored_translations: List[str] = []

            for translated_text in translations:
                cleaned = self._sanitize_chat_response(translated_text, log_changes=False)
                limited = limit_characters(cleaned)
                restored_translations.append(limited)

            return {
                "success": True,
                "translations": restored_translations,
                "usage": usage
            }
        except (KeyError, IndexError) as e:
            self._log(f"解析批量API响应失败: {str(e)}, 响应: {response_data}")
            return {"success": False, "text": "翻译失败: 无法解析API响应"}
        except Exception as e:
            self._log(f"处理批量API响应时发生错误: {str(e)} \n 批量API响应数据：{response_data}")
            return {"success": False, "text": f"翻译失败: {str(e)}"}
    
    def _sanitize_chat_response(self, content: str, log_changes: bool = True) -> str:
        if not content:
            return ""

        original_length = len(content)
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<think(?:ing)?>[^<]*(?:</think(?:ing)?>)?', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()

        if log_changes and len(cleaned) != original_length:
            self._log(f"已移除思维链内容 (减少了{original_length - len(cleaned)}个字符)")

        max_length = 10000
        if len(cleaned) > max_length:
            self._log(f"警告: 翻译结果过长，已截断至{max_length}字符")
            cleaned = cleaned[:max_length] + "...(内容过长已截断)"

        return cleaned

    def _extract_batch_translations(self, raw_content: str, expected_count: int) -> Optional[List[str]]:
        if not raw_content:
            return None

        cleaned = self._strip_code_fences(raw_content.strip())

        parsed_array = None
        try:
            parsed_json = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed_json = None

        if isinstance(parsed_json, dict):
            candidate = parsed_json.get("translations")
            if isinstance(candidate, list):
                parsed_array = candidate
            elif isinstance(candidate, dict):
                parsed_array = list(candidate.values())
        elif isinstance(parsed_json, list):
            parsed_array = parsed_json

        if isinstance(parsed_array, list):
            cleaned_results = [self._clean_translation_entry(item) for item in parsed_array]
            if len(cleaned_results) == expected_count:
                return cleaned_results

        array_match = re.search(r'\[[\s\S]*\]', cleaned)
        if array_match:
            try:
                parsed_array = json.loads(array_match.group(0))
                if isinstance(parsed_array, list):
                    cleaned_results = [self._clean_translation_entry(item) for item in parsed_array]
                    if len(cleaned_results) == expected_count:
                        return cleaned_results
            except json.JSONDecodeError:
                pass

        lines = [self._clean_translation_entry(line) for line in cleaned.splitlines() if line.strip() != ""]
        if len(lines) == expected_count:
            return lines

        return None

    def _clean_translation_entry(self, item: Any) -> str:
        if isinstance(item, str):
            text = item
        else:
            text = json.dumps(item, ensure_ascii=False) if item is not None else ""

        text = self._strip_code_fences(text.strip())
        text = re.sub(r'^(?:\d+|\(\d+\)|\[\d+\])[\.\):]?\s*', '', text)
        return text

    def _strip_code_fences(self, content: str) -> str:
        if not content:
            return ""

        trimmed = content.strip()
        if trimmed.startswith("```"):
            newline_index = trimmed.find('\n')
            if newline_index != -1:
                trimmed = trimmed[newline_index + 1:]

            if trimmed.endswith("```"):
                trimmed = trimmed[:-3]

            return trimmed.strip()

        return content

    def test_connection(self) -> Dict[str, Any]:
        """
        测试API连接
        
        Returns:
            测试结果字典
        """
        api_url = self.config.get("api_url")
        api_key = self.config.get("api_key")
        model_name = self.config.get("model_name")
        
        if not api_url:
            return {"success": False, "message": "错误: API URL不能为空"}
        if not api_key:
            return {"success": False, "message": "错误: API Key不能为空"}
        if not model_name:
            return {"success": False, "message": "错误: 模型名称不能为空"}
        
        try:
            temperature = float(self.config.get("temperature", 1.0))
        except (ValueError, TypeError):
            temperature = 1.0
        
        try:
            max_tokens = int(self.config.get("max_tokens", 8192))
        except (ValueError, TypeError):
            max_tokens = 8192
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "Hello, can you hear me? Please respond with a simple yes."
            }
        ]
        
        data = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        self._log(f"API URL: {api_url}")
        self._log(f"Model: {model_name}")
        self._log(f"Temperature: {temperature}")
        self._log(f"Max Tokens: {max_tokens}")
        self._log("正在发送测试请求...")
        
        try:
            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                try:
                    reply_content = response_data["choices"][0]["message"]["content"]
                    result = {
                        "success": True,
                        "message": f"API响应成功！回复内容: {reply_content}",
                        "content": reply_content
                    }
                    
                    if "usage" in response_data:
                        usage = response_data["usage"]
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)
                        
                        result["usage"] = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }
                        
                        self._log(f"Token使用: 请求={prompt_tokens}, 回复={completion_tokens}, 总计={total_tokens}")

                    self._log("配置测试成功！API响应正常。")
                    
                    return result
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"解析API响应时出错: {str(e)}",
                        "raw_response": response.text
                    }
            else:
                return {
                    "success": False,
                    "message": f"API请求失败，HTTP状态码: {response.status_code}",
                    "error_details": response.text
                }
        except requests.exceptions.Timeout:
            return {"success": False, "message": "错误: API请求超时"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "错误: 无法连接到API服务器，请检查网络或API URL是否正确"}
        except Exception as e:
            return {"success": False, "message": f"测试配置时发生错误: {str(e)}"}
    
    def get_model_list(self) -> Dict[str, Any]:
        """
        获取模型列表
        
        Returns:
            包含模型列表的字典
        """
        api_url = self.config.get("api_url", "")
        api_key = self.config.get("api_key", "")
        
        if not api_url:
            return {"success": False, "message": "获取模型列表失败: API URL不能为空"}
        if not api_key:
            return {"success": False, "message": "获取模型列表失败: API Key不能为空"}
        
        if not api_url.endswith("/chat/completions"):
            api_url = api_url.rstrip("/") + "/chat/completions"
        
        base_url_parts = api_url.split("/")
        base_url = "/".join(base_url_parts[:3])
        
        endpoints = [
            f"{base_url}/models",
            f"{base_url}/v1/models",
            f"{api_url.replace('chat/completions', 'models')}"
        ]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        
        success = False
        models_list = []
        
        for endpoint in endpoints:
            try:
                self._log(f"正在尝试API端点: {endpoint}")
                response = requests.get(endpoint, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if "data" in response_data and isinstance(response_data["data"], list):
                        models_list = [model.get("id", "未知") for model in response_data["data"]]
                    elif "models" in response_data and isinstance(response_data["models"], list):
                        models_list = [model.get("id", model.get("name", "未知")) for model in response_data["models"]]
                    else:
                        self._log(f"无法识别的API响应格式，原始响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                        for key, value in response_data.items():
                            if isinstance(value, list):
                                self._log(f"找到可能的模型列表键：{key}，包含 {len(value)} 个项目")
                    
                    if models_list:
                        success = True
                        break
                
            except requests.exceptions.RequestException:
                continue
        
        if not success:
            self._log("无法获取模型列表，所有已知的API端点尝试均失败")
            self._log("请尝试手动查询您的API提供商的文档以获取正确的模型列表端点")
            return {"success": False, "message": "无法获取模型列表，请检查API配置"}
        
        return {"success": True, "models": models_list} 