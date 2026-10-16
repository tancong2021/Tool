import calendar
import re
from datetime import date

from tqdm import tqdm

from core import LoginManager
from settings import Config
from utils import get_logger
from utils.logger import setup_logger


class ClockRecordManager:
    def __init__(self, session, token, beginDate=None, endDate=None,
                 taskName="", projectName="", checkStauts=1):
        self.logger = get_logger()
        self.session = session
        self.beginDate = beginDate or None
        self.endDate = endDate or None
        self.taskName = taskName
        self.projectName = projectName
        self.checkStauts = checkStauts
        self.requestHeader = {
            **Config.BASE_HEADERS,
            "Authorization": f"Bearer {token}",
        }

    def getClockInfo(self):
        """获取考勤记录，按月分段、每段分页，返回 {考勤id: 精简记录}"""
        segments = self.split_by_month(self.beginDate, self.endDate)
        self.logger.info(f"=> 正在获取考勤记录，共 {len(segments)} 个月份段...")

        records = {}
        page_size = 1000

        for seg_begin, seg_end in segments:
            params = {
                "checkStauts": self.checkStauts,
                "params[beginDate]": seg_begin,
                "params[endDate]": seg_end,
            }
            # 为空就不带
            if self.taskName:
                params["taskName"] = self.taskName
            if self.projectName:
                params["projectName"] = self.projectName

            page = 1
            pbar = None
            try:
                while True:
                    params["pageNum"] = page
                    params["pageSize"] = page_size
                    response = self.session.get(
                        Config.CLOCK_API_URL,
                        headers=self.requestHeader,
                        params=params,
                        timeout=(Config.REQUEST_TIMEOUT, 60),
                    )
                    response.raise_for_status()
                    result = response.json()

                    if int(result.get("code", -1)) != 200:
                        raise RuntimeError(f"获取考勤记录失败: {result.get('msg')}")

                    if pbar is None:
                        try:
                            total = int(result.get("total"))
                        except (TypeError, ValueError):
                            total = None
                        pbar = tqdm(total=total, unit="条",
                                    desc=f"正在获取 {seg_begin[:7]} 考勤")

                    rows = self._extract_rows(result)
                    before = len(records)
                    for row in rows:
                        records[row["id"]] = {
                            "id": row["id"],
                            "user_id": row.get("userId"),
                            "user_name": row.get("userName"),
                            "task_date": row.get("taskDate"),
                            "shift_start": row.get("ruleStartTime"),
                            "shift_end": row.get("ruleEndTime"),
                            "start_result": row.get("startResult"),
                            "end_result": row.get("endResult"),
                        }
                    pbar.update(len(records) - before)

                    if not rows or len(rows) < page_size or (pbar.total and pbar.n >= pbar.total):
                        break
                    page += 1
            finally:
                if pbar is not None:
                    pbar.close()

        self.logger.info(f"=> 获取考勤记录完成，共 {len(records)} 条")
        return len(records)

    @staticmethod
    def _extract_rows(result):
        rows = result.get("rows")
        if rows is None:
            data = result.get("data")
            rows = data.get("rows") if isinstance(data, dict) else data
        return rows or []

    def split_by_month(self,begin=None, end=None):
        """把起止日期按自然月拆段，返回 [(开始时间, 结束时间), ...]

        - begin、end 都为空：默认查当月（本月 1 号到今天）
        - 支持 "10-1"、"10.1"、"10/1"、"10月1日"（补成今年）和 "2025-12-1"（用输入的年份）
        - 开始补 00:00:00，结束补 23:59:59（今天也直接补，不截断）
        - 结束日期不能晚于今天，开始日期不能晚于结束日期
        """
        today =  date.today()

        if not begin and not end:
            begin_d, end_d = today.replace(day=1), today
        elif begin and end:
            begin_d = self._parse_date(begin, today.year)
            end_d = self._parse_date(end, today.year)
        else:
            raise ValueError("开始日期和结束日期需要同时填写，或都不填（默认查当月）")

        if end_d > today:
            raise ValueError(f"考勤查询的结束日期 {end_d} 不能晚于今天 {today}")
        if begin_d > end_d:
            raise ValueError(
                f"考勤查询的开始日期 {begin_d} 晚于结束日期 {end_d}，跨年请写明年份，如 2025-12-1 到 2026-2-2"
            )

        segments = []
        year, month = begin_d.year, begin_d.month
        while (year, month) <= (end_d.year, end_d.month):
            last_day = calendar.monthrange(year, month)[1]
            seg_begin = begin_d if (year, month) == (begin_d.year, begin_d.month) else date(year, month, 1)
            seg_end = end_d if (year, month) == (end_d.year, end_d.month) else date(year, month, last_day)
            segments.append((f"{seg_begin.isoformat()} 00:00:00", f"{seg_end.isoformat()} 23:59:59"))
            month += 1
            if month > 12:
                year, month = year + 1, 1
        return segments

    @staticmethod
    def _parse_date(text, default_year):
        """解析单个日期，没写年份就用 default_year"""
        nums = re.findall(r"\d+", str(text))
        if len(nums) == 2:
            year, month, day = default_year, int(nums[0]), int(nums[1])
        elif len(nums) == 3:
            year, month, day = int(nums[0]), int(nums[1]), int(nums[2])
        else:
            raise ValueError(f"无法识别的考勤日期格式: {text!r}")
        try:
            return date(year, month, day)
        except ValueError:
            raise ValueError(f"考勤查询的日期不存在: {year}-{month}-{day}") from None


if __name__ == "__main__":
    setup_logger()
    login = LoginManager(Config.USERNAME, Config.PASSWORD)
    session = login.get_login_session()
    clock = ClockRecordManager(session, login.get_token(), "10-1", "10-16")
    print(clock.getClockInfo())
