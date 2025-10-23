"""
HTTP服务器模块，提供翻译服务的HTTP接口
"""

import http.server
import socketserver
import urllib.parse
import queue
import threading
import time
import concurrent.futures
import socket
import json
import traceback
from typing import Dict, Any, Callable, Optional, List

from core.utils import convert_punctuation

class TranslationHandler(http.server.BaseHTTPRequestHandler):
    """翻译请求处理类"""
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    @staticmethod
    def _safe_excerpt(text: str, limit: int = 200) -> str:
        if text is None:
            return ""
        if len(text) <= limit:
            return text
        return f"{text[:limit]}...(truncated)"

    @staticmethod
    def _print_json(label: str, data: Any):
        try:
            serialized = json.dumps(data, ensure_ascii=False)
        except Exception:
            serialized = str(data)
        print(f"[server] {label}: {serialized}")
    
    def __init__(self, *args, config=None, app=None, api_client=None, **kwargs):
        self.config = config
        self.app = app
        self.api_client = api_client
        self.result_queue = queue.Queue()
        super().__init__(*args, **kwargs)
    
    @classmethod
    def close_resources(cls):
        """关闭资源"""
        if cls.executor:
            try:
                print("开始关闭线程池资源...")
                cls.executor.shutdown(wait=False)

                cls.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                shutdown_success = False
                try:
                    executor_ref = cls.executor
                    shutdown_thread = threading.Thread(
                        target=lambda: executor_ref.shutdown(wait=True) if executor_ref else None,
                        daemon=True
                    )
                    shutdown_thread.start()
                    
                    shutdown_thread.join(2.0)
                    if not shutdown_thread.is_alive():
                        shutdown_success = True
                except Exception as e:
                    print(f"等待线程池关闭时出错: {str(e)}")
                
                if not shutdown_success:
                    print("线程池关闭超时，将强制关闭")
                
                cls.executor = None
                print("线程池资源已关闭")
            except Exception as e:
                print(f"关闭线程池时出错: {str(e)}")
                cls.executor = None
    
    def _log(self, message: str):
        print(f"[server] {message}")

    def log_message(self, format, *args):
        """屏蔽默认的HTTP请求日志"""
        pass
    
    def update_conversation_history(self, user_text, ai_response):
        """更新对话历史"""
        if self.app:
            self.app.update_conversation_history(user_text, ai_response)
    
    def do_POST(self):
        """处理POST请求（批量翻译）"""
        request_id = f"req-{int(time.time() * 1000)}-{threading.get_ident()}"
        self.request_id = request_id
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''

            # self._log(f"[{request_id}] 收到批量翻译POST请求，正文长度 {content_length} 字节")

            if not raw_body:
                self._write_plain_response(400, "请求体为空")
                self._log(f"[{request_id}] 错误: 收到空的批量请求体")
                return

            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError:
                self._write_plain_response(400, "请求体不是有效的JSON")
                excerpt = self._safe_excerpt(raw_body)
                self._log(f"[{request_id}] 错误: 批量请求体不是有效的JSON，raw='{excerpt}'")
                return

            # self._print_json("收到请求", payload)

            texts = payload.get("texts")
            if not isinstance(texts, list) or len(texts) == 0:
                self._write_plain_response(400, "缺少texts数组")
                self._log(f"[{request_id}] 错误: 批量请求缺少texts数组")
                self._print_json(f"[{request_id}] 无效payload", payload)
                return

            normalized_texts = [str(item) if item is not None else "" for item in texts]
            print(f"[{request_id}] 接收到批量翻译请求，共 {len(normalized_texts)} 条")

            self._submit_translation(normalized_texts)
            result = self._wait_for_result()

            if not result.get("success"):
                error_message = result.get("error", "翻译失败")
                self._log(f"[{request_id}] 批量翻译失败: {error_message}")
                self._print_json(f"[{request_id}] 批量翻译失败详情", result)
                self._write_plain_response(500, error_message)
                return

            translations = result.get("translations", [])
            usage = result.get("usage")

            response_payload: Dict[str, Any] = {
                "translations": translations
            }

            if usage:
                response_payload["usage"] = usage

            self._write_json_response(200, response_payload)
            # self._log(f"[{request_id}] 批量翻译完成，共 {len(translations)} 条")

        except Exception as e:
            self._log(f"[{request_id}] 处理批量请求时出错: {str(e)}")
            self._log(traceback.format_exc())
            self._write_plain_response(500, f"服务器错误: {str(e)}")
    
    def _process_translation_request(self, payload):
        """处理翻译请求"""
        try:
            request_id = getattr(self, "request_id", "req-unknown")
            if self.app and getattr(self.app, 'is_shutting_down', False):
                self._log(f"[{request_id}] 应用程序正在关闭，取消翻译请求")
                self.result_queue.put({"success": False, "error": "翻译失败: 应用程序正在关闭"})
                return

            if not self.api_client:
                self._log(f"[{request_id}] 错误: API客户端未初始化")
                self.result_queue.put({"success": False, "error": "翻译失败: API客户端未初始化"})
                return

            texts_to_translate = payload if isinstance(payload, list) else [payload]
            texts_to_translate = [str(item) if item is not None else "" for item in texts_to_translate]

            result = self.api_client.translate_batch(texts_to_translate, None)
            # self._print_json(f"[{request_id}] 翻译响应", result)

            if not result.get("success"):
                error_message = result.get("text") or result.get("error") or "翻译失败"
                self._log(f"[{request_id}] 翻译接口返回失败: {error_message}")
                self._print_json(f"[{request_id}] 失败响应详情", result)
                self.result_queue.put({"success": False, "error": error_message})
                return

            translations = result.get("translations", [])
            if len(translations) != len(texts_to_translate):
                self._log(
                    f"[{request_id}] 翻译失败: 返回数量 {len(translations)} 与请求数量 {len(texts_to_translate)} 不匹配"
                )
                self.result_queue.put({"success": False, "error": "翻译失败: 返回数量与请求数量不匹配"})
                return

            translations = [convert_punctuation(item) for item in translations]

            usage = result.get("usage")
            if usage and self.app:
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)
                self.app.update_token_count(prompt_tokens, completion_tokens, total_tokens)

            if self.app:
                for original, translated in zip(texts_to_translate, translations):
                    self.update_conversation_history(original, translated)

            if self.app and getattr(self.app, 'is_shutting_down', False):
                self._log(f"[{request_id}] 应用程序正在关闭，放弃返回翻译结果")
                return

            # self._log(f"[{request_id}] 批量翻译完成: {len(translations)} 条")

            self.result_queue.put({
                "success": True,
                "translations": translations,
                "usage": usage
            })
        except Exception as e:
            error_message = f"翻译失败: {str(e)}"
            request_id = getattr(self, "request_id", "req-unknown")
            self._log(f"[{request_id}] 翻译处理异常: {str(e)}")
            self._log(traceback.format_exc())
            if not (self.app and getattr(self.app, 'is_shutting_down', False)):
                self.result_queue.put({"success": False, "error": error_message})

    def _submit_translation(self, payload):
        if TranslationHandler.executor is None:
            TranslationHandler.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

        TranslationHandler.executor.submit(self._process_translation_request, payload)

    def _wait_for_result(self, timeout: float = 180.0) -> Dict[str, Any]:
        start_time = time.time()
        request_id = getattr(self, "request_id", "req-unknown")

        while time.time() - start_time < timeout:
            if self.app and getattr(self.app, 'is_shutting_down', False):
                self._log(f"[{request_id}] 应用程序正在关闭，中断等待翻译结果")
                return {"success": False, "error": "翻译失败: 应用程序正在关闭"}

            try:
                return self.result_queue.get(timeout=0.5)
            except queue.Empty:
                continue

        self._log(f"[{request_id}] 错误: 翻译处理超时")
        return {"success": False, "error": "翻译失败: 处理超时"}

    def _write_plain_response(self, status_code: int, message: str):
        payload = (message or "").encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _write_json_response(self, status_code: int, payload: Dict[str, Any]):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """多线程HTTP服务器"""
    
    allow_reuse_address = True
    daemon_threads = True
    
    def shutdown(self):
        """关闭服务器"""
        try:
            super().shutdown()
        except Exception as e:
            print(f"服务器关闭时出错: {str(e)}")


class ServerManager:
    """服务器管理类"""
    
    def __init__(self, config, app=None, api_client=None):
        """
        初始化服务器管理类
        
        Args:
            config: 配置信息
            app: 应用程序实例
            api_client: API客户端实例
        """
        self.config = config
        self.app = app
        self.api_client = api_client
        self.server = None
        self.server_thread = None
        self.is_running = False

    def _log(self, message: str):
        print(f"[server] {message}")
    
    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.settimeout(1)
            test_socket.bind(('', port))
            return True
        except socket.error:
            return False
        finally:
            test_socket.close()
    
    def start(self) -> bool:
        """启动服务器"""
        if self.is_running:
            self._log("服务已经在运行中")
            return False
        
        try:
            try:
                port = int(self.config.get("port", 6800))
                if port < 1 or port > 65535:
                    raise ValueError("端口号必须在1-65535之间")
            except ValueError as e:
                self._log(f"端口号无效: {str(e)}")
                return False
            
            if not self.is_port_available(port):
                self._log(f"端口 {port} 已被占用，请尝试其他端口")
                return False
            
            def handler_factory(*args, **kwargs):
                return TranslationHandler(
                    *args, 
                    config=self.config, 
                    app=self.app,
                    api_client=self.api_client,
                    **kwargs
                )
            
            self.server = ThreadedHTTPServer(("", port), handler_factory)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.is_running = True
            
            self._log(f"服务已启动，监听端口 {port}")
            
            return True
        except Exception as e:
            self._log(f"启动服务失败: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """停止服务器"""
        if not self.is_running or not self.server:
            self._log("服务未在运行")
            return False
        
        try:
            self._log("正在取消所有待处理的请求...")
            
            TranslationHandler.close_resources()

            self._log("正在关闭服务器...")

            if self.server:
                self.server.shutdown()
                self.server.server_close()

            if self.server_thread:
                self.server_thread.join(timeout=5.0)

            if self.server_thread and self.server_thread.is_alive():
                self._log("服务器线程关闭超时，将强制关闭...")
            else:
                self._log("服务器已正常关闭")

            self.server = None
            self.server_thread = None
            self.is_running = False

            self._log("服务已停止")

            return True
        except Exception as e:
            self._log(f"停止服务器时出错: {str(e)}")
            self.server = None
            self.server_thread = None
            self.is_running = False
            
            self._log("服务已强制停止")
            
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            "is_running": self.is_running,
            "port": self.config.get("port", "未设置")
        } 