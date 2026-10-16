from datetime import date
import re
import requests
from tqdm import tqdm
from core import LoginManager
from settings import Config
from utils import get_logger
from utils.logger import setup_logger


class UserManager:
    def __init__(self, session, token, beginDate, endDate):
        self.logger = get_logger()
        self.beginDate =beginDate  if beginDate  else None
        self.endDate =endDate if endDate  else None
        self.session = session if session is not None else requests.Session()
        self.token = token
        self.requestHeader = {
            **Config.BASE_HEADERS,
            "Authorization": f"Bearer {self.token}"
        }

    def getUserInfo(self):
        """获取用户列表，分页获取，返回 {id: {name, id_no, phone, bank_name}}
        beginDate / endDate 为空时，不带时间参数（查全部）"""
        self.logger.info("=> 正在获取用户信息...")
        params = {
            "userName": "",
            "authStatus": 2,  # 已认证
            "stuFlag": "N",
            "idNo": "",
        }

        if self.beginDate and self.endDate:
            self.beginDate, self.endDate = self.formattedTime(self.beginDate, self.endDate)
            params["params[beginDate]"] = self.beginDate
            params["params[endDate]"] = self.endDate
            self.logger.info(f"=> 获取用户信息的时间范围: {self.beginDate} ~ {self.endDate}")
        else:
            self.logger.info("=> 获取用户信息未选择时间，查询全部")

        users = {}
        page, page_size = 1, 1000
        pbar = None

        try:
            while True:
                params["pageNum"] = page
                params["pageSize"] = page_size
                response = self.session.get(
                    Config.USER_API_URL,
                    headers=self.requestHeader,
                    params=params,
                    timeout=(Config.REQUEST_TIMEOUT, 60),
                )
                response.raise_for_status()
                result = response.json()

                if int(result.get("code", -1)) != 200:
                    raise RuntimeError(f"=> 获取用户信息失败: {result.get('msg')}")

                # 第一页拿到 total，创建进度条
                if pbar is None:
                    raw = result.get("total")
                    if raw is None and isinstance(result.get("data"), dict):
                        raw = result["data"].get("total")
                    try:
                        total = int(raw)
                    except (TypeError, ValueError):
                        total = None
                    pbar = tqdm(total=total, desc="正在获取用户信息", unit="人")

                rows = self._extract_rows(result)
                before = len(users)
                for row in rows:
                    users[row["id"]] = {
                        "id": row["id"],  # 标记号，用于关联考勤
                        "name": row.get("userName"),
                        "id_no": row.get("idNo"),
                        "phone": row.get("userPhone"),
                        "bank_name": row.get("bankName"),
                    }
                pbar.update(len(users) - before)  # tqdm 是增量更新

                # 结束条件：本页为空 / 不满一页 / 已取够 total
                if not rows or len(rows) < page_size or (pbar.total and len(users) >= pbar.total):
                    break
                page += 1
        finally:
            if pbar is not None:
                pbar.close()

        self.logger.info(f"=> 获取用户信息完成，共 {len(users)} 条")
        return users

    @staticmethod
    def _extract_rows(result):
        """兼容 {"rows": [...]} 和 {"data": {"rows": [...]}} 两种结构"""
        rows = result.get("rows")
        if rows is None:
            data = result.get("data")
            rows = data.get("rows") if isinstance(data, dict) else data
        return rows or []


    def formattedTime(self, beginDate, endDate):
        return self.format_date_range(beginDate, endDate)

    def format_date_range(self, begin, end):
        """把用户输入的起止日期统一成 YYYY-MM-DD

        支持的输入：
            "10-1"、"10.1"、"10/1"、"10月1日"  -> 补全为今年
            "2025-12-1"、"2025.12.1"            -> 使用输入的年份
        规则：
            1. 结束日期不能晚于今天
            2. 开始日期不能晚于结束日期（如 "12-1" 到 "2-2" 会报错，需要写明年份）

        Returns:
            tuple[str, str]: (开始日期, 结束日期)，格式 YYYY-MM-DD
        Raises:
            ValueError: 日期格式不对或不合理
        """
        today = date.today()
        begin_d = self._parse_date(begin, today.year)
        end_d = self._parse_date(end, today.year)

        if end_d > today:
            raise ValueError(f"=> 查询用户信息的结束日期 {end_d} 不能晚于今天 {today}")
        if begin_d > end_d:
            raise ValueError(
                f"=> 查询用户信息的开始日期 {begin_d} 晚于结束日期 {end_d}，"
                f"=> 如果查询用户信息的日期跨年请写明年份，如 2025-12-1 到 2026-2-2"
            )
        return begin_d.isoformat(), end_d.isoformat()

    def _parse_date(self, text, default_year):
        """解析单个日期，没写年份就用 default_year"""
        nums = re.findall(r"\d+", str(text))
        if len(nums) == 2:  # 月 日
            year, month, day = default_year, int(nums[0]), int(nums[1])
        elif len(nums) == 3:  # 年 月 日
            year, month, day = int(nums[0]), int(nums[1]), int(nums[2])
        else:
            raise ValueError(f"=> 无法识别查询用户信息的日期格式: {text!r}")
        try:
            return date(year, month, day)
        except ValueError:
            raise ValueError(f"=> 查询用户信息的日期不存在: {year}-{month}-{day}") from None



if __name__ == "__main__":
    setup_logger()
    login = LoginManager(Config.USERNAME, Config.PASSWORD)
    login_session = login.get_login_session()
    user = UserManager(login_session, login.get_token(), "", "")
    print(user.getUserInfo())
