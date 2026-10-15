#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块：统一的日志配置
author:tancong
datetime:2026-2-17
"""

import logging
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from settings import Config


class SensitiveFilter(logging.Filter):
    """日志脱敏：避免密码、token 被写进日志"""
    # 日志里出现这些字段时，值替换成 ***（密码、token、加密后的登录数据等）
    _SENSITIVE = re.compile(
        r'(?i)([\'"]?(?:password|pwd|token|authorization|decryptData|mobileCode)[\'"]?\s*[:=]\s*[\'"]?)'
        r'(?:Bearer\s+)?[^\s\'",}&]+'
    )
    def filter(self, record):


        record.msg = self._SENSITIVE.sub(r'\1***', record.getMessage())  # 先把消息拼完整，再替换敏感值
        record.args = ()                                            # 消息已拼好，清掉参数避免重复格式化
        return True                                                 # True = 这条日志继续输出


def setup_logger(log_dir=None, name='MTTime', level=logging.INFO, log_prefix='MTTime', keep_days=30):
    """设置日志系统，返回 logger（重复调用安全，不会重复输出）"""
    log_path = Path(log_dir) if log_dir else Config.LOG_DIR
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)       # logger 本身放行所有级别，由各 handler 决定输出什么
    logger.propagate = False             # 不向 root 传递，避免重复打印

    for h in logger.handlers[:]:         # 重复 setup 时，先移除并关闭旧 handler
        logger.removeHandler(h)
        h.close()

    # ---------- 文件日志 ----------
    log_file = log_path / f"{log_prefix}.log"
    file_handler = TimedRotatingFileHandler(
        log_file, when='midnight', backupCount=keep_days, encoding='utf-8', delay=True
    )
    file_handler.setLevel(logging.DEBUG)             # 文件记录所有细节
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(filename)s:%(lineno)d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    file_handler.addFilter(SensitiveFilter())
    logger.addHandler(file_handler)

    # ---------- 控制台日志 ----------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)                  # 控制台默认只显示 INFO 及以上
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    console_handler.addFilter(SensitiveFilter())
    logger.addHandler(console_handler)

    # ---------- 未捕获的异常也写进日志 ----------
    def _log_uncaught(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):  # Ctrl+C 不当成错误
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("未捕获的异常", exc_info=(exc_type, exc, tb))

    sys.excepthook = _log_uncaught

    logger.info(f"=> 日志文件路径: {log_file}")
    return logger


def get_logger(name='MTTime'):
    """获取已配置好的 logger（在其他模块里用）"""
    return logging.getLogger(name)


if __name__ == '__main__':
    setup_logger()
    logger = get_logger()
    logger.debug('debug')
    logger.info('info')
    logger.warning('warning')
    logger.error('error')