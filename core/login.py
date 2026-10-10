"""
登入模块
"""
import requests


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