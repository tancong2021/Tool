"""
这是一个配置类主要存放一些配置数据

"""
import sys
from pathlib import Path


class Config:
    """配置类"""

    # ==================== 账号配置 ====================
    USERNAME = "XXXXXX"
    PASSWORD = "XXXX"

    # ==================== 路径配置 ====================
    # 获取根目录
    if getattr(sys, 'frozen', False):
        BASE_DIR = Path(sys.executable).parent
    else:
        BASE_DIR = Path(__file__).parent.parent


    # ==================== API接口配置 ====================
    BASE_API_URL = "https://mtime.ngu-u.com"
    LOGIN_API_URL = f"{BASE_API_URL}/adminApi/auth/login/v2" # 登入API接口
    CAPTCHA_API_URL = f"{BASE_API_URL}/adminApi/code"        # 获取验证码API接口



