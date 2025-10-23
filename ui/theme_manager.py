"""
主题管理模块，处理系统主题检测与应用
"""

import winreg
class ThemeManager:
    """主题管理类"""
    
    def __init__(self, root=None):
        """
        初始化主题管理器
        
        Args:
            root: Tk/Tkinter窗口根对象
        """
        self.root = root
        self.current_theme = self.detect_windows_theme()
    
    def log(self, message: str):
        """记录日志"""
        print(f"[theme] {message}")
    
    def detect_windows_theme(self) -> str:
        """
        检测Windows系统主题是否为暗色模式
        
        Returns:
            返回对应的ttkbootstrap主题名称
        """
        try:
            # 打开注册表路径
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            
            # 读取AppsUseLightTheme值，0表示暗色模式，1表示亮色模式
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            
            # 关闭注册表
            winreg.CloseKey(key)
            
            # 根据系统主题返回相应的ttkbootstrap主题
            if value == 0:  # 暗色模式
                return "darkly"
            else:  # 亮色模式
                return "litera"
        except Exception as e:
            self.log(f"检测系统主题出错: {str(e)}")
            # 出错时使用默认暗色主题
            return "darkly"
    
    def check_and_update_theme(self) -> bool:
        """
        检查并更新主题
        
        Returns:
            如果主题已更新返回True，否则返回False
        """
        if not self.root:
            return False
            
        try:
            new_theme = self.detect_windows_theme()
            if new_theme != self.current_theme:
                self.log(f"检测到系统主题变化: {self.current_theme} -> {new_theme}")
                self.current_theme = new_theme
                self.root.style.theme_use(new_theme)
                return True
        except Exception as e:
            self.log(f"切换主题出错: {str(e)}")
        
        return False
    
    def set_root(self, root):
        """设置根窗口对象"""
        self.root = root
    
    def get_current_theme(self) -> str:
        """获取当前主题"""
        return self.current_theme 