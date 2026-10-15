#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密模块
处理RSA加密相关操作
"""
import json
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

from settings import Config
from utils.logger import get_logger


class RSAEncryptor:
    """RSA加密器"""
    def __init__(self, public_key):
        """初始化
        Args:
            public_key: RSA公钥（PEM格式字符串）
        """
        self.public_key = Config.PUBLIC_KEY
        self.logger = get_logger()
        self.logger.debug("=> RSA加密器初始化完成...")

    def encrypt(self, data):
        """加密数据
        Args:
            data: 待加密的数据（字典）
        Returns:
            str: base64编码的加密字符串
        Raises:
            Exception: 加密失败时抛出异常
        """
        try:
            self.logger.debug("=> 开始RSA加密数据...")

            # 加载公钥
            cipher = PKCS1_v1_5.new(RSA.import_key(self.public_key))

            # 转为JSON字符串（无空格）
            json_str = json.dumps(data, separators=(',', ':'))

            # RSA加密
            encrypted = cipher.encrypt(json_str.encode('utf-8'))

            # Base64编码
            result = base64.b64encode(encrypted).decode('utf-8')

            self.logger.debug(f"=> 数据加密完成，长度: {len(result)} 字符")

            return result

        except Exception as e:
            self.logger.error(f"=> RSA加密失败: {e}", exc_info=True)
            raise

    def encrypt_login_data(self, username, password, mobile_code=""):
        """加密登录数据
        Args:
            username: 用户名
            password: 密码
            mobile_code: 手机验证码（可选）
        Returns:
            str: 加密后的字符串
        """
        data = {
            "username": username,
            "password": password,
            "mobileCode": mobile_code
        }
        return self.encrypt(data)

if __name__ == '__main__':
    encryptor = RSAEncryptor(Config.PUBLIC_KEY)
    print(encryptor.encrypt_login_data("username", "password"))
