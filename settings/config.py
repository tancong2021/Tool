import json
import sys
import time
from pathlib import Path


class Config:
    """配置类"""
    TOKEN_TTL = 12 * 3600          # 本地认为 token 的有效期（秒），按平台实际过期时间改

    def __init__(self):
        # ================================ 账号配置 ======================================
        self.USERNAME = "XXXXXX"
        self.PASSWORD = "XXXX"

        # ================================ 路径配置 ======================================
        if getattr(sys, 'frozen', False):
            self.BASE_DIR = Path(sys.executable).parent
        else:
            self.BASE_DIR = Path(__file__).parent.parent
        self.OUTPUT_DIR = self.BASE_DIR / "output"
        self.TOKEN_FILE_PATH = self.BASE_DIR / "token.json"        # token 持久化文件

        # ================================ API接口配置 ===================================
        self.BASE_API_URL = "https://mtime.ngu-u.com"
        self.LOGIN_API_URL = f"{self.BASE_API_URL}/adminApi/auth/login/v2"
        self.CAPTCHA_API_URL = f"{self.BASE_API_URL}/adminApi/code"
        self.ATTENDANCE_API_URL = f"{self.BASE_API_URL}/adminApi/system/mtime/user/list"

        self.token = self.load_token()                         # 启动时自动读取，没有则为 ""

    # ------------------------------ token 持久化 ------------------------------
    def save_token(self, token):
        """登录成功后调用：存到内存，同时写入文件"""
        self.token = token
        data = {"token": token, "saved_time": int(time.time())}
        self.TOKEN_FILE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load_token(self):
        """读取本地 token；文件不存在、损坏、超过 TOKEN_TTL 都返回空串"""
        try:
            data = json.loads(self.TOKEN_FILE_PATH.read_text(encoding="utf-8"))
            if time.time() - data.get("saved_time", 0) < self.TOKEN_TTL:
                return data.get("token", "")
        except (OSError, ValueError):
            pass
        return ""

    def clear_token(self):
        """接口返回 401 时调用，丢掉失效的 token"""
        self.token = ""
        self.TOKEN_FILE_PATH.unlink(missing_ok=True)

    # ------------------------------ 获取 token ------------------------------
    @staticmethod
    def extract_token(result: dict) -> str:
        """从登录接口返回的 JSON 里取 token（兼容 {"token":..} 和 {"data":{"token":..}}）"""
        if result.get("code") != 200:
            raise RuntimeError(f"登录失败: {result.get('msg')}")
        token = result.get("token") or (result.get("data") or {}).get("token")
        if not token:
            raise RuntimeError(f"登录返回里没有 token: {result}")
        return token

    @staticmethod
    def login(session, login_url, username, password, **extra):
        """调登录接口并返回 token。验证码等字段通过 extra 传，如 code='1234', uuid='xxx'"""
        payload = {"username": username, "password": password, **extra}
        resp = session.post(login_url, json=payload, timeout=30)
        resp.raise_for_status()
        return Config.extract_token(resp.json())