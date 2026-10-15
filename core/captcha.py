import base64
import operator
import os
import re
import subprocess
import sys
from pathlib import Path
import requests
from settings import Config
from utils import get_logger
# 以下沿用你原有的导入：Config, get_logger, Console, Prompt, Panel,
# RICH_AVAILABLE, OCR_AVAILABLE, ddddocr

try:
    import ddddocr
except ImportError:
    ddddocr = None

try:
    from rich.console import Console
    from rich.prompt import Prompt
except ImportError:
    Console = Prompt = None

_OPS = {'+': operator.add, '-': operator.sub, '*': operator.mul}
# OCR 常见的符号误识别，统一归一化
_TRANS = str.maketrans({
    '×': '*', 'x': '*', 'X': '*', '＋': '+', '－': '-', '—': '-', '–': '-',
    '＝': '=', '？': '?', ' ': '',
})
_EXPR_RE = re.compile(r'(\d+)([+\-*])(\d+)')


class CaptchaHandler:
    """验证码处理器：优先 OCR 自动识别，失败再人工输入"""

    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.logger = get_logger()
        self.console = Console()
        self.ocr = self._init_ocr()

    def _init_ocr(self):
        """初始化 OCR，失败返回 None（后续自动退回人工输入）"""
        try:
            import ddddocr  # 延迟导入，启动更快
            ocr = ddddocr.DdddOcr(show_ad=False)
        except ImportError:
            self.logger.warning("=> ddddocr 未安装，验证码将手动输入")
        except Exception as e:
            self.logger.warning(f"=> OCR 验证码初始化失败: {e}")
        else:
            self.logger.info("=> 0CR 验证码识别已启用")
            return ocr
        return None


    # ---------- 对外接口 ----------
    def get_captcha(self, force_manual=False):
        """获取验证码
        Args:
            force_manual: True 时跳过 OCR 直接人工输入（OCR 答错重试时用）
        Returns:
            tuple: (captcha_uuid, captcha_code)
        """
        response = self.session.get(Config.CAPTCHA_API_URL, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if data.get('code') != 200:
            raise RuntimeError(f"=> 获取验证码失败: {data}")

        captcha_uuid = data['uuid']
        img_bytes = base64.b64decode(data['img'])
        self.logger.info(f"验证码获取成功, captcha_uuid: {captcha_uuid[:16]}...")

        code = None if force_manual else self._auto_solve(img_bytes)
        if code is None:
            path = self._save_image(img_bytes)
            self._open_image(path)
            code = self._ask_user(path)

        if not code:
            raise ValueError("验证码不能为空")
        return captcha_uuid, code

    # ---------- 自动识别 ----------
    def _auto_solve(self, img_bytes):
        """OCR 识别并计算，失败返回 None"""
        if not self.ocr:
            return None
        try:
            raw = self.ocr.classification(img_bytes)
            answer = self._solve_expr(raw)
            if answer is None:
                self.logger.warning(f"=> OCR 结果无法解析: {raw!r}")
                return None
            self.logger.info(f"=> OCR 识别: {raw!r} -> {answer}")
            return answer
        except Exception as e:
            self.logger.warning(f"=> OCR 识别异常: {e}")
            return None

    @staticmethod
    def _solve_expr(text):
        """解析 '7+1=?' 这类算式，返回字符串答案"""
        m = _EXPR_RE.search(text.translate(_TRANS))
        if not m:
            return None
        a, op, b = int(m[1]), m[2], int(m[3])
        return str(_OPS[op](a, b))

    # ---------- 人工兜底 ----------
    def _save_image(self, img_bytes):
        path = Config.CAPTCHA_IMG_DIR/ "captcha.png"
        Path(path).write_bytes(img_bytes)
        return path

    def _open_image(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))
            else:
                cmd = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.run([cmd, str(path)], check=False)
        except Exception as e:
            self.logger.warning(f"=> 无法自动打开验证码图片: {e}")

    def _ask_user(self, path):
        """统一的输入入口：有 rich 用 rich，没有就退回 input"""
        hint = "验证码计算题请输入结果（如 8-4=? 输入 4）"
        if self.console:
            self.console.print(f"[cyan]📸 {Path(path).name}[/cyan]  [dim]{hint}[/dim]")
            return Prompt.ask("[bold green]👉 验证码答案[/bold green]").strip()
        print(f"\n验证码: {path}\n{hint}")
        return input("=> 请输入验证码答案: ").strip()

if __name__ == '__main__':
    CaptchaHandler = CaptchaHandler()
    captcha_uuid, code = CaptchaHandler.get_captcha()
    print(code)