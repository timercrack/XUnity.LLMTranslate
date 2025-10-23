"""
UI组件模块，包含各种UI控件的封装
"""

import tkinter as tk
from tkinter import scrolledtext
import ttkbootstrap as ttk
from typing import Callable, Optional, Dict, Any, List

class ConfigPanel:
    """配置面板组件"""
    
    def __init__(self, parent, default_font, bold_font, config: Optional[Dict[str, Any]] = None):
        """
        初始化配置面板
        
        Args:
            parent: 父容器
            default_font: 默认字体
            bold_font: 粗体字体
            config: 配置信息
        """
        self.parent = parent
        self.default_font = default_font
        self.bold_font = bold_font
        self.config = config or {}
        
        self.api_url_entry = None
        self.api_key_entry = None
        self.model_name_var = None
        self.model_name_combobox = None
        self.get_models_button = None
        self.port_var = None
        self.port_entry = None
        self.temperature_var = None
        self.temperature_entry = None
        self.max_tokens_var = None
        self.max_tokens_entry = None
        self.batch_prompt_text = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建控件"""
        # 创建配置框架
        self.config_frame = ttk.LabelFrame(self.parent, text="API 配置", padding=10)
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # API URL
        ttk.Label(self.config_frame, text="API URL:", font=self.default_font).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        url_container = ttk.Frame(self.config_frame)
        url_container.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        url_container.columnconfigure(0, weight=1)

        self.api_url_entry = ttk.Entry(url_container, width=60, font=self.default_font)
        self.api_url_entry.grid(row=0, column=0, sticky=tk.EW)

        tip_font = ("Segoe UI", 9, "italic")
        tip_label = ttk.Label(
            url_container, 
            text="提示：如API无法正常调用可以试试在地址后面加上/v1哦！", 
            font=tip_font, 
            foreground="gray"
        )
        tip_label.grid(row=1, column=0, sticky=tk.W)
        
        # API Key
        ttk.Label(self.config_frame, text="API Key:", font=self.default_font).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_entry = ttk.Entry(self.config_frame, width=60, font=self.default_font, show="*")
        self.api_key_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 模型名称
        ttk.Label(self.config_frame, text="模型名称:", font=self.default_font).grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        model_frame = ttk.Frame(self.config_frame)
        model_frame.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        model_frame.columnconfigure(0, weight=1)
        
        self.model_name_var = tk.StringVar()
        self.model_name_combobox = ttk.Combobox(
            model_frame, 
            textvariable=self.model_name_var,
            width=50, 
            font=self.default_font,
            state="normal"
        )
        self.model_name_combobox.grid(row=0, column=0, sticky=tk.EW)
        
        try:
            self.get_models_button = ttk.Button(
                model_frame,
                text="获取模型列表",
                bootstyle="info-outline",
                width=12,
                cursor="hand2"
            )
        except Exception:
            self.get_models_button = ttk.Button(
                model_frame,
                text="获取模型列表",
                width=12,
                cursor="hand2"
            )
        self.get_models_button.grid(row=0, column=1, padx=(5, 0))
        
        # 参数面板
        params_frame = ttk.Frame(self.config_frame)
        params_frame.grid(row=4, column=0, columnspan=2, sticky=tk.N, padx=5, pady=5)
        
        for i in range(6):
            params_frame.columnconfigure(i, weight=1)

        # 所有设置居中对齐
        ttk.Label(params_frame, text="监听端口:", font=self.default_font).grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(params_frame, width=8, font=self.default_font, textvariable=self.port_var)
        self.port_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(params_frame, text="温度:", font=self.default_font).grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)
        self.temperature_var = tk.StringVar()
        self.temperature_entry = ttk.Entry(params_frame, width=8, font=self.default_font, textvariable=self.temperature_var)
        self.temperature_entry.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(params_frame, text="最大Token数量:", font=self.default_font).grid(row=0, column=4, sticky=tk.E, padx=5, pady=5)
        self.max_tokens_var = tk.StringVar()
        self.max_tokens_entry = ttk.Entry(params_frame, width=8, font=self.default_font, textvariable=self.max_tokens_var)
        self.max_tokens_entry.grid(row=0, column=5, sticky=tk.W, padx=5)

        # 批量提示
        prompt_frame = ttk.LabelFrame(self.parent, text="批量翻译提示", padding=10)
        prompt_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.batch_prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, height=6, font=self.default_font)
        self.batch_prompt_text.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        self.config_frame.columnconfigure(1, weight=1)
    
    def set_get_models_callback(self, callback: Callable):
        """设置获取模型列表的回调函数"""
        self.get_models_button.config(command=callback)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        api_url = self.api_url_entry.get().strip()
        api_url = api_url.rstrip("/")
        
        if not api_url.endswith("/chat/completions"):
            api_url += "/chat/completions"
        
        try:
            temperature = float(self.temperature_var.get().strip())
            temperature = max(0.0, min(2.0, temperature))
        except (ValueError, TypeError):
            temperature = 1.0
            self.temperature_var.set(str(temperature))
            
        try:
            max_tokens = int(self.max_tokens_var.get().strip())
            max_tokens = max(1, max_tokens)
        except (ValueError, TypeError):
            max_tokens = 4096
            self.max_tokens_var.set(str(max_tokens))
            
        config_copy = dict(self.config) if self.config else {}
        system_prompt_text = self.batch_prompt_text.get("1.0", tk.END).strip() if self.batch_prompt_text else ""

        config_copy.update({
            "api_url": api_url,
            "api_key": self.api_key_entry.get().strip(),
            "model_name": self.model_name_var.get().strip(),
            "port": self.port_var.get().strip(),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt_text
        })

        self.config = config_copy
        return config_copy
    
    def load_config(self, config: Dict[str, Any]):
        """加载配置"""
        if not config:
            return

        self.config = config
            
        api_url_display = config.get("api_url", "")
        if api_url_display.endswith("/chat/completions"):
            api_url_display = api_url_display[:-len("/chat/completions")]
            
        self.api_url_entry.delete(0, tk.END)
        self.api_url_entry.insert(0, api_url_display)
        
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, config.get("api_key", ""))
        
        self.model_name_var.set(config.get("model_name", ""))
        
        if self.batch_prompt_text:
            self.batch_prompt_text.delete("1.0", tk.END)
            self.batch_prompt_text.insert("1.0", config.get("system_prompt", ""))
        
        self.port_var.set(config.get("port", ""))
        self.temperature_var.set(str(config.get("temperature", 1.0)))
        self.max_tokens_var.set(str(config.get("max_tokens", 4096)))
    
    def update_model_list(self, models_list: List[str]):
        """更新模型列表"""
        if not models_list:
            return
            
        current_value = self.model_name_var.get()
        
        self.model_name_combobox['values'] = models_list
        
        if current_value not in models_list and models_list:
            self.model_name_var.set(models_list[0])
        else:
            self.model_name_var.set(current_value)


class TokenPanel:
    """Token统计面板组件"""
    
    def __init__(self, parent, default_font, bold_font):
        """初始化Token统计面板"""
        self.parent = parent
        self.default_font = default_font
        self.bold_font = bold_font
        
        self.token_label = None
        self.reset_token_button = None
        
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建控件"""
        token_frame = ttk.LabelFrame(self.parent, text="Token 使用统计", padding=10)
        token_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.token_label = ttk.Label(
            token_frame, 
            text="请求: 0  |  回复: 0  |  总计: 0", 
            font=self.bold_font
        )
        self.token_label.pack(side=tk.LEFT, padx=5)
        
        try:
            self.reset_token_button = ttk.Button(
                token_frame,
                text="重置计数",
                bootstyle="secondary-outline",
                width=15,
                cursor="hand2"
            )
        except Exception:
            self.reset_token_button = ttk.Button(
                token_frame,
                text="重置计数",
                width=15,
                cursor="hand2"
            )
        self.reset_token_button.pack(side=tk.RIGHT, padx=5)
    
    def set_reset_callback(self, callback: Callable):
        """设置重置Token计数的回调函数"""
        self.reset_token_button.config(command=callback)
    
    def update_token_count(self, prompt_tokens=0, completion_tokens=0, total_tokens=0):
        """更新Token计数"""
        try:
            prompt_tokens = int(prompt_tokens) if prompt_tokens else 0
            completion_tokens = int(completion_tokens) if completion_tokens else 0
            total_tokens = int(total_tokens) if total_tokens else 0
        except (ValueError, TypeError):
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        
        if total_tokens > 0 and prompt_tokens == 0 and completion_tokens == 0:
            total_diff = total_tokens - (self.prompt_tokens + self.completion_tokens)
            if total_diff > 0:
                self.total_tokens += total_diff
        else:
            self.total_tokens += total_tokens
        
        self._update_display()
    
    def _update_display(self):
        """更新显示"""
        self.token_label.config(
            text=f"请求: {self.prompt_tokens}  |  回复: {self.completion_tokens}  |  总计: {self.total_tokens}"
        )
    
    def reset_count(self):
        """重置计数"""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self._update_display()
    
    def get_counts(self) -> Dict[str, int]:
        """获取当前计数"""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }


class ControlPanel:
    """控制面板组件"""
    
    def __init__(self, parent, default_font):
        """初始化控制面板"""
        self.parent = parent
        self.default_font = default_font
        
        self.toggle_server_button = None
        self.test_config_button = None
        self.save_config_button = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建控件"""
        button_frame = ttk.Frame(self.parent, padding=5)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        try:
            self.toggle_server_button = ttk.Button(
                button_frame, 
                text="启动服务", 
                bootstyle="success",
                width=15,
                cursor="hand2"
            )
        except Exception:
            self.toggle_server_button = ttk.Button(
                button_frame, 
                text="启动服务", 
                width=15,
                cursor="hand2"
            )
        self.toggle_server_button.pack(side=tk.LEFT, padx=5)
        
        try:
            self.test_config_button = ttk.Button(
                button_frame, 
                text="测试配置", 
                bootstyle="info",
                width=15,
                cursor="hand2"
            )
        except Exception:
            self.test_config_button = ttk.Button(
                button_frame, 
                text="测试配置", 
                width=15,
                cursor="hand2"
            )
        self.test_config_button.pack(side=tk.LEFT, padx=5)
        
        try:
            self.save_config_button = ttk.Button(
                button_frame, 
                text="保存配置", 
                bootstyle="warning",
                width=15,
                cursor="hand2"
            )
        except Exception:
            self.save_config_button = ttk.Button(
                button_frame, 
                text="保存配置", 
                width=15,
                cursor="hand2"
            )
        self.save_config_button.pack(side=tk.LEFT, padx=5)
    
    def set_toggle_server_callback(self, callback: Callable):
        """设置切换服务状态的回调函数"""
        self.toggle_server_button.config(command=callback)
    
    def set_test_config_callback(self, callback: Callable):
        """设置测试配置的回调函数"""
        self.test_config_button.config(command=callback)
    
    def set_save_config_callback(self, callback: Callable):
        """设置保存配置的回调函数"""
        self.save_config_button.config(command=callback)
    
    def update_server_button(self, is_running: bool):
        """更新服务按钮状态"""
        if is_running:
            self.toggle_server_button.config(text="停止服务")
            try:
                self.toggle_server_button.configure(bootstyle="danger")
            except Exception:
                pass
        else:
            self.toggle_server_button.config(text="启动服务")
            try:
                self.toggle_server_button.configure(bootstyle="success")
            except Exception:
                pass


class LogPanel:
    """日志面板组件"""
    
    def __init__(self, parent, default_font):
        """初始化日志面板"""
        self.parent = parent
        self.default_font = default_font
        
        self.log_text = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建控件"""
        log_frame = ttk.LabelFrame(self.parent, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=self.default_font)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
    
    def add_log(self, message: str):
        """添加日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED) 