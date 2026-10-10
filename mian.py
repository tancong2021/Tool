"""
程序主入口
"""
from Crypto.PublicKey import RSA

from settings import Config


def main():
    pass





if __name__ == "__main__":
    config = Config()
    main()
    print(RSA.import_key(config.PUBLIC_KEY))