"""
登入模块
"""
import json
import time

import requests

from settings import Config
from utils import RSAEncryptor, get_logger
from utils.logger import setup_logger


class LoginManager:
    """登录管理器"""
    def __init__(self, username, password):
        """初始化
        Args:
            username: 用户名
            password: 密码
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None
        self.encryptor = RSAEncryptor(Config.PUBLIC_KEY)
        self.token = self.load_token()

        # 初始化子模块
        self.logger = get_logger()
        self.logger.info(f"登录管理器初始化完成, 用户: {username}")


    def login(self):
        for attempt in range(Config.MAX_RETRY_ATTEMPTS):
            try:
                self.logger.info(f"=> 开始第 {attempt + 1}/{Config.MAX_RETRY_ATTEMPTS} 次用户登录尝试")



            except Exception as e:
                self.logger.error(f"=> 用户登录异常: {e}", exc_info=True)





        # ------------------------------ token 持久化 ------------------------------
        def save_token(self, token):
            """登录成功后调用：存到内存，同时写入文件"""
            self.token = token
            data = {"token": token, "saved_time": int(time.time())}
            self.TOKEN_FILE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        def load_token(self):
            """读取本地 token；文件不存在、损坏、超过 TOKEN_TTL 都返回空串"""
            try:
                data = json.loads(Config.TOKEN_FILE_PATH.read_text(encoding="utf-8"))
                if time.time() - data.get("saved_time", 0) < self.TOKEN_TTL:
                    return data.get("token", "")
            except (OSError, ValueError):
                pass
            return ""

        def clear_token(self):
            """接口返回 401 时调用，丢掉失效的 token"""
            self.token = ""
            Config.TOKEN_FILE_PATH.unlink(missing_ok=True)

        # ------------------------------ 获取 token ------------------------------
        @staticmethod
        def extract_token(result: dict) -> str:
            """从登录接口返回的 JSON 里取 token（兼容 {"token":..} 和 {"data":{"token":..}}）"""
            if result.get("code") != 200:
                raise RuntimeError(f"=> 登录失败: {result.get('msg')}")
            token = result.get("token") or (result.get("data") or {}).get("token")
            if not token:
                raise RuntimeError(f"=> 登录返回里没有 token: {result}")
            return token

if __name__ == "__main__":
    setup_logger()
    login_manager = LoginManager("username", "password")