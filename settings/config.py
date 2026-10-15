import json
import sys
import time
from pathlib import Path


class Config:
    """配置类"""
    TOKEN_TTL = 12 * 3600          # 本地认为 token 的有效期（秒），按平台实际过期时间改
    MAX_RETRY_ATTEMPTS = 3         # 最大请求次数
    REQUEST_TIMEOUT = 300          # 单次请求时间(秒)
    # ================================ 账号配置 ======================================
    USERNAME = "XXXXXX"
    PASSWORD = "XXXX"


    PUBLIC_KEY = PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAquI4cHpCD/KY0iK8Zf4r
        3UmYtcUrAjEvhm5qeE9uAmjSgX2t2J0+YV1cF/XWywHLRV3b0RDfNq32fMy8xiX3
        z3rkt4ykfjoUmZgOqCfUAp5FGaOJrJ5k71zV7u/X3P7/g1nKaUpamBB5Pv9CWcZp
        zvJjguF9DgbkDNK13ncM9T0c7YdG+D9gQlUb3YWBIKsFNGBL3z+sl33CmiETzcS3
        qlQg0BB/repkAQLqKB9AqLnYbJ8XwY/WU4GcsC+0bKPIoXz4eMHdDA2prtV7Y+sJ
        JedfHhrJnHbZAZMkERHH12X1N7kuAS6kWK2hLqC1FQu6OQIaZZ9gsUMXTV8P6B+y
        HwIDAQAB
        -----END PUBLIC KEY-----"""


    # ================================ 路径配置 ======================================
    if getattr(sys, 'frozen', False):
        BASE_DIR = Path(sys.executable).parent
    else:
        BASE_DIR = Path(__file__).parent.parent
        OUTPUT_DIR = BASE_DIR / "output"
        TOKEN_FILE_PATH = BASE_DIR / "token"        # token 持久化文件

    # ================================ API接口配置 ===================================
    BASE_API_URL = "https://mtime.ngu-u.com"
    LOGIN_API_URL = f"{BASE_API_URL}/adminApi/auth/login/v2"
    CAPTCHA_API_URL = f"{BASE_API_URL}/adminApi/code"
    ATTENDANCE_API_URL = f"{BASE_API_URL}/adminApi/system/mtime/user/list"
    CAPTCHA_IMG_DIR = BASE_DIR / "captcha"
    LOG_DIR = BASE_DIR / "log"

    @classmethod
    def ensure_dirs(cls):
        """确保所有必要的目录存在"""
        for dir_path in [cls.CAPTCHA_IMG_DIR,
                         cls.LOG_DIR,
                         cls.OUTPUT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)



if __name__ == '__main__':
    config = Config()
    config.ensure_dirs()