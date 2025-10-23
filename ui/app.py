"""
主应用程序模块，整合所有UI组件和功能
"""

import os
import time
import threading
import tkinter as tk
import ttkbootstrap as ttk
from core.config_manager import ConfigManager
from core.api_client import APIClient
from core.server import ServerManager, TranslationHandler
from ui.theme_manager import ThemeManager
from ui.components import ConfigPanel, TokenPanel, ControlPanel

class TranslationServiceApp:
    """翻译服务应用程序类"""
    
    def __init__(self):
        """初始化应用程序"""
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 创建主窗口
        self.root = ttk.Window(title="XUnity大模型翻译批量处理版", themename=self.theme_manager.get_current_theme())
        self._center_window(1024, 768)
        
        # 设置主题管理器的根窗口
        self.theme_manager.set_root(self.root)
        
        # 初始化标志
        self.is_shutting_down = False
        
        # 创建字体
        self.default_font = ("Segoe UI", 10)
        self.bold_font = ("Segoe UI", 10, "bold")
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # 创建API客户端
        self.api_client = APIClient(self.config)
        
        # 创建服务器管理器
        self.server_manager = ServerManager(
            self.config,
            app=self,
            api_client=self.api_client
        )
        
        # 创建UI组件
        self._init_ui_components()
        
        # 设置窗口关闭回调
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 设置定时器
        self._start_timers()
    
    def _init_ui_components(self):
        """初始化UI组件"""
        # 配置面板
        self.config_panel = ConfigPanel(self.main_frame, self.default_font, self.bold_font, self.config)
        self.config_panel.set_get_models_callback(self._get_model_list)
        # 确保默认配置被加载到界面上
        self.config_panel.load_config(self.config)
        
        # Token统计面板
        self.token_panel = TokenPanel(self.main_frame, self.default_font, self.bold_font)
        self.token_panel.set_reset_callback(self.reset_token_count)
        
        # 控制面板
        self.control_panel = ControlPanel(self.main_frame, self.default_font)
        self.control_panel.set_toggle_server_callback(self.toggle_server)
        self.control_panel.set_test_config_callback(self.test_config)
        self.control_panel.set_save_config_callback(self.save_config)
        
    def _log(self, message: str):
        """记录日志"""
        print(message)

    def _center_window(self, width: int, height: int):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _start_timers(self):
        """启动定时器"""
        # 每10秒检查一次主题变化
        self.root.after(10000, self._check_theme_timer)
        
        # UI更新定时器
        self.root.after(100, self._update_ui_timer)
    
    def _check_theme_timer(self):
        """检查主题变化的定时器"""
        if self.is_shutting_down:
            return
        
        self.theme_manager.check_and_update_theme()
        
        # 重新安排定时器
        self.root.after(10000, self._check_theme_timer)
    
    def _update_ui_timer(self):
        """更新UI的定时器"""
        if self.is_shutting_down:
            return
            
        # 重新安排定时器
        self.root.after(100, self._update_ui_timer)
    
    def run(self):
        """运行应用程序"""
        self._log("翻译服务应用已启动")
        self.root.mainloop()
    
    def toggle_server(self):
        """切换服务器状态"""
        if self.server_manager.is_running:
            if self.server_manager.stop():
                self.control_panel.update_server_button(False)
        else:
            # 获取最新配置
            self.config = self.config_panel.get_config()
            
            # 更新服务器管理器和API客户端的配置
            self.server_manager.config = self.config
            self.api_client.config = self.config
            
            if self.server_manager.start():
                self.control_panel.update_server_button(True)
    
    def test_config(self):
        """测试API配置"""
        self._log("正在测试API配置...")
        
        # 获取最新配置
        self.config = self.config_panel.get_config()
        
        # 更新API客户端的配置
        self.api_client.config = self.config
        
        threading.Thread(
            target=self._test_config_thread,
            daemon=True
        ).start()
    
    def _test_config_thread(self):
        """测试配置的线程方法"""
        try:
            result = self.api_client.test_connection()
            
            if result["success"]:
                self._log(result["message"])
                
                if "usage" in result:
                    usage = result["usage"]
                    self.update_token_count(
                        usage.get('prompt_tokens', 0),
                        usage.get('completion_tokens', 0),
                        usage.get('total_tokens', 0)
                    )
            else:
                self._log(result["message"])
                if "error_details" in result:
                    self._log(f"错误详情: {result['error_details']}")
        except Exception as e:
            self._log(f"测试配置过程中发生错误: {str(e)}")
    
    def _get_model_list(self):
        """获取模型列表"""
        try:
            self._log("正在获取模型列表...")
            
            # 获取最新配置
            self.config = self.config_panel.get_config()
            
            # 更新API客户端的配置
            self.api_client.config = self.config
            
            # 禁用按钮
            button = getattr(self.config_panel, "get_models_button", None)
            if button:
                button.config(state=tk.DISABLED)
            
            threading.Thread(
                target=self._get_model_list_thread,
                daemon=True
            ).start()
        except Exception as e:
            self._log(f"获取模型列表时发生错误: {str(e)}")
            button = getattr(self.config_panel, "get_models_button", None)
            if button:
                button.config(state=tk.NORMAL)
    
    def _get_model_list_thread(self):
        """获取模型列表的线程方法"""
        try:
            result = self.api_client.get_model_list()
            
            if result["success"] and "models" in result:
                models_list = result["models"]
                
                if models_list:
                    self.root.after(0, lambda: self.config_panel.update_model_list(models_list))
                    self._log(f"成功获取模型列表，共 {len(models_list)} 个模型")
                else:
                    self._log("模型列表为空")
            else:
                if "message" in result:
                    self._log(result["message"])
        except Exception as e:
            self._log(f"获取模型列表过程中发生错误: {str(e)}")
        finally:
            def enable_button():
                button = getattr(self.config_panel, "get_models_button", None)
                if button:
                    button.config(state=tk.NORMAL)
            self.root.after(0, enable_button)
    
    def save_config(self):
        """保存配置"""
        try:
            # 获取最新配置
            self.config = self.config_panel.get_config()
            
            # 保存配置
            if self.config_manager.save_config(self.config):
                pass
            else:
                self._log("保存配置失败")
        except Exception as e:
            self._log(f"保存配置时发生错误: {str(e)}")
    
    def update_token_count(self, prompt_tokens=0, completion_tokens=0, total_tokens=0):
        """更新Token计数"""
        self.root.after(0, lambda: self.token_panel.update_token_count(prompt_tokens, completion_tokens, total_tokens))
    
    def reset_token_count(self):
        """重置Token计数"""
        self.token_panel.reset_count()
        self._log("Token计数已重置")
    
    def update_conversation_history(self, user_text, ai_response):
        """历史记录功能已移除，保留方法保持兼容"""
        return
    
    def on_close(self):
        """窗口关闭事件处理"""
        self.is_shutting_down = True
        
        self._log("正在关闭应用程序，请稍候...")
        close_start_time = time.time()
        
        absolute_kill_timer = threading.Timer(5.0, lambda: os._exit(0))
        absolute_kill_timer.daemon = True
        absolute_kill_timer.start()
        
        shutdown_thread = threading.Thread(
            target=self._background_shutdown,
            daemon=True
        )
        shutdown_thread.start()
        
        self.root.after(300, self._final_destroy)
    
    def _background_shutdown(self):
        """后台关闭处理"""
        try:
            if self.server_manager.is_running:
                print("正在后台线程中停止服务器...")
                self.server_manager.stop()
            
            try:
                print("正在后台线程中清理线程资源...")
                TranslationHandler.close_resources()
                print("线程资源已清理完毕")
            except Exception as e:
                print(f"清理线程资源时出错: {str(e)}")
            
            print("后台关闭操作完成")
        except Exception as e:
            print(f"后台关闭操作出错: {str(e)}")
    
    def _final_destroy(self):
        """最终销毁窗口"""
        try:
            self.root.destroy()
        except Exception as e:
            print(f"销毁窗口时出错: {str(e)}")
            self._force_exit()
    
    def _force_exit(self):
        """强制退出"""
        print("程序关闭超时，强制退出...")
        os._exit(0) 