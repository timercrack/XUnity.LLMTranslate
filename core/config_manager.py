"""
配置管理模块，负责加载和保存配置
"""

import os
import configparser
from typing import Dict, Any

# 默认配置
DEFAULT_CONFIG = {
    "api_url": "https://api.deepseek.com",
    "api_key": "sk-1111111111111111111",
    "model_name": "deepseek-chat",
    "temperature": 1.3,
    "max_tokens": 8192,
    "system_prompt": """你是一个游戏翻译模型，能够流畅通顺地将任意游戏文本翻译成简体中文，并在理解上下文的前提下准确使用人称代词。不要进行任何额外的格式修改，不允许擅自添加原文中不存在的代词；你的回答只能包含翻译文本，不得输出翻译以外的说明、建议或翻译过程描述，也不允许在译文后附加注释。请将译文中的中文标点全部替换为英文标点，若原文是单个字母或符号则直接原样返回。务必确保译文符合中文语言习惯并贴合游戏内容的语境，可根据语气和风格做恰当调整，同时考虑词语的文化内涵和地区差异；译文需达到“信达雅”的要求：忠实内容、表达通顺、语言优雅。Ostranauts（星际漂流者）是一款黑色风格的硬核太空模拟游戏，请让译文契合这一题材。你将收到一个JSON对象，其中texts字段包含待翻译字符串数组；数组每一个元素是一个完整字符串，不得拆分或合并。请仅返回一个紧凑的JSON数组，数组长度与输入texts相同，元素顺序一致，每个元素只对应一条译文，不得添加任何多余内容。""",
    "port": "6800"
}

CONFIG_FILE = "config.ini"

class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = DEFAULT_CONFIG.copy()
        
    def load_config(self):
        """加载配置"""
        try:
            if not os.path.exists(self.config_file):
                print("[config] 配置文件不存在，将使用默认配置")
                return self.config
            
            config_parser = configparser.ConfigParser()
            config_parser.read(self.config_file, encoding='utf-8')
            
            if "API" in config_parser:
                settings = config_parser["API"]
                
                api_url = settings.get('api_url', DEFAULT_CONFIG["api_url"])
                if not api_url:
                    api_url = DEFAULT_CONFIG["api_url"]
                if not api_url.endswith("/chat/completions"):
                    api_url = api_url.rstrip("/")
                    api_url += "/chat/completions"
                self.config["api_url"] = api_url
                
                self.config["api_key"] = settings.get('api_key', DEFAULT_CONFIG["api_key"])
                self.config["model_name"] = settings.get('model_name', DEFAULT_CONFIG["model_name"])
                self.config["system_prompt"] = settings.get('system_prompt', DEFAULT_CONFIG["system_prompt"])
                self.config["port"] = settings.get('port', DEFAULT_CONFIG["port"])
                
                temperature_value = settings.get('temperature', DEFAULT_CONFIG["temperature"])
                if temperature_value is None:
                    temperature_value = DEFAULT_CONFIG["temperature"]
                try:
                    self.config["temperature"] = float(temperature_value)
                except (ValueError, TypeError):
                    self.config["temperature"] = float(DEFAULT_CONFIG["temperature"])
                    
                max_tokens_value = settings.get('max_tokens', DEFAULT_CONFIG["max_tokens"])
                if max_tokens_value is None:
                    max_tokens_value = DEFAULT_CONFIG["max_tokens"]
                try:
                    self.config["max_tokens"] = int(max_tokens_value)
                except (ValueError, TypeError):
                    self.config["max_tokens"] = int(DEFAULT_CONFIG["max_tokens"])
                    
                print("[config] 配置已从文件加载")
            else:
                print("[config] 配置文件中缺少API部分，将使用默认配置")
        except Exception as e:
            print(f"[config] 加载配置时出错: {str(e)}")
            self.config = DEFAULT_CONFIG.copy()
            
        return self.config
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置"""
        try:
            self.config = config
            
            api_url = config["api_url"]
            if api_url.endswith("/chat/completions"):
                api_url = api_url[:-len("/chat/completions")]
            
            config_parser = configparser.ConfigParser()
            config_parser["API"] = {
                'api_url': api_url,
                'api_key': config["api_key"],
                'model_name': config["model_name"],
                'system_prompt': config.get("system_prompt", DEFAULT_CONFIG["system_prompt"]),
                'port': config["port"],
                'temperature': str(config["temperature"]),
                'max_tokens': str(config["max_tokens"]),
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config_parser.write(f)
            
            print("[config] 配置已保存")
                
            return True
        except Exception as e:
            print(f"[config] 保存配置失败: {str(e)}")
            return False 