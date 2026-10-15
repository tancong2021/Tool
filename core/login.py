import json
import time

import requests

from core.captcha import CaptchaHandler
from settings import Config
from utils import get_logger, RSAEncryptor


class LoginManager:
    """登录管理器：本地 token 有效就直接用，否则登录并保存"""

    def __init__(self, username, password):
        self.logger = get_logger()
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.user_info = {}
        self.encryptor = RSAEncryptor(Config.PUBLIC_KEY)
        self.captcha_handler = CaptchaHandler(self.session)
        self.token = self.load_token()              # 启动时读取本地有效 token
        self.logger.info(f"=> 登录管理器初始化完成, 用户: {username}")

    # ------------------------------ 对外入口 ------------------------------
    def get_token(self, force=False):
        """获取可用 token

        Args:
            force: True 时忽略本地缓存，强制重新登录（接口返回 401 后用）
        Returns:
            str | None: token，登录失败返回 None
        """
        if not force and self.token:
            self.logger.info("=> 使用本地缓存 token，无需登录")
            return self.token
        return self.token if self.login() else None

    # ------------------------------ 登录 ------------------------------
    def login(self):
        for attempt in range(Config.MAX_RETRY_ATTEMPTS):
            try:
                self.logger.info(f"=> 开始第 {attempt + 1}/{Config.MAX_RETRY_ATTEMPTS} 次登录尝试")

                # 第一次允许 OCR，失败后改人工，避免 OCR 反复读错
                captcha_uuid, captcha_code = self.captcha_handler.get_captcha(
                    force_manual=(attempt > 0)
                )
                encrypted_data = self.encryptor.encrypt_login_data(self.username, self.password)

                response = self.session.post(
                    Config.LOGIN_API_URL,
                    json={
                        "adminCaptchaCheck": True,
                        "code": captcha_code,
                        "decryptData": encrypted_data,
                        "uuid": captcha_uuid,
                    },
                    timeout=Config.REQUEST_TIMEOUT,
                )
                result = response.json()
                self.logger.info(f"=> 响应: code={result.get('code')}, msg={result.get('msg')}")

                if result.get("code") == 200:
                    self.user_info = result.get("data") or {}
                    self.save_token(self.extract_token(result))
                    self.logger.info("=> 登录成功")
                    return True

                self.logger.warning(f"=> 登录失败: {result.get('msg')}")

            except Exception as e:
                self.logger.error(f"=> 用户登录异常: {e}", exc_info=True)

        self.logger.error("=> 登录失败，已达最大重试次数")
        return False

    @staticmethod
    def extract_token(result):
        """响应结构: {"code": 200, "data": {"access_token": "..."}}"""
        token = (result.get("data") or {}).get("access_token")
        if not token:
            raise RuntimeError(f"=> 登录返回里没有 data.access_token: {result}")
        return token

    # ------------------------------ token 持久化 ------------------------------
    def _read_token_file(self):
        """读取 token 文件，不存在或损坏返回空字典"""
        try:
            return json.loads(Config.TOKEN_FILE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _is_fresh(data):
        """文件里的 token 是否存在且未过期"""
        return bool(data.get("token")) and \
            time.time() - data.get("saved_time", 0) < Config.TOKEN_TTL

    def load_token(self):
        """读取本地 token；不存在、损坏、过期都返回空串"""
        data = self._read_token_file()
        return data["token"] if self._is_fresh(data) else ""

    def save_token(self, token):
        """保存 token：与文件中相同且未过期则不重写，否则写入新的"""
        self.token = token
        data = self._read_token_file()
        if data.get("token") == token and self._is_fresh(data):
            self.logger.info("=> token 与本地一致且未过期，无需重新保存")
            return
        Config.TOKEN_FILE_PATH.write_text(
            json.dumps({"token": token, "saved_time": int(time.time())}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.logger.info("=> token 已保存到本地")

    def clear_token(self):
        """接口返回 401 时调用，丢掉失效的 token"""
        self.token = ""
        Config.TOKEN_FILE_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    manager = LoginManager(Config.USERNAME, Config.PASSWORD)
    manager.login()
    token = manager.get_token()
    print("token:", token)