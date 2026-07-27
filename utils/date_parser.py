"""中文日期解析工具"""
import re
import datetime
from dateutil import parser as du_parser
from dateutil.relativedelta import relativedelta
from utils.date_context import get_date_context


# 中文数字映射
_CN_NUM = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '十一': 11, '十二': 12, '两': 2,
}

# 星期映射
_WEEKDAY_CN = {
    '周一': 0, '周二': 1, '周三': 2, '周四': 3, '周五': 4, '周六': 5, '周日': 6,
    '星期一': 0, '星期二': 1, '星期三': 2, '星期四': 3, '星期五': 4, '星期六': 5, '星期天': 6, '星期日': 6,
    '礼拜一': 0, '礼拜二': 1, '礼拜三': 2, '礼拜四': 3, '礼拜五': 4, '礼拜六': 5, '礼拜天': 6, '礼拜日': 6,
}


def parse_relative_date(text: str, today: datetime.date = None) -> datetime.date | None:
    """解析相对日期文本，返回绝对日期

    支持：
    - 今天/今天/今
    - 明天/明日/明
    - 后天/后日
    - 大后天
    - 下周X / 下周一
    - 下个月X号 / 下月X日
    - N天后 / N天之后
    - N周后
    """
    if today is None:
        today = get_date_context().today

    text = text.strip()

    # 绝对日期（YYYY-MM-DD 或 YYYY/MM/DD）
    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日', '%Y年%m月%d号']:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    # 今天
    if text in ('今天', '今日', '今'):
        return today

    # 明天
    if text in ('明天', '明日', '明'):
        return today + datetime.timedelta(days=1)

    # 后天
    if text in ('后天', '后日'):
        return today + datetime.timedelta(days=2)

    # 大后天
    if text in ('大后天',):
        return today + datetime.timedelta(days=3)

    # N天后
    m = re.match(r'(\d+)\s*天[后之]', text)
    if m:
        return today + datetime.timedelta(days=int(m.group(1)))

    # N周后
    m = re.match(r'(\d+)\s*周[后之]', text)
    if m:
        return today + datetime.timedelta(weeks=int(m.group(1)))

    # N个月后
    m = re.match(r'(\d+)\s*个?月[后之]', text)
    if m:
        return today + relativedelta(months=int(m.group(1)))

    # 下周一/下周三 ...
    for cn, wd in _WEEKDAY_CN.items():
        if cn in text:
            days_ahead = wd - today.weekday()
            if '下周' in text or '下个星期' in text or '下礼拜' in text:
                days_ahead += 7
            if days_ahead <= 0:
                days_ahead += 7
            return today + datetime.timedelta(days=days_ahead)

    # 下个月X号
    m = re.match(r'下个?月\s*(\d+|[一二三四五六七八九十]+)\s*[号日]', text)
    if m:
        day_str = m.group(1)
        day = _CN_NUM.get(day_str, int(day_str) if day_str.isdigit() else 1)
        return today.replace(day=1) + relativedelta(months=1, day=min(day, 28))

    # 尝试 dateutil 兜底
    try:
        return du_parser.parse(text, fuzzy=True).date()
    except Exception:
        pass

    return None


def parse_chinese_datetime(text: str) -> tuple[datetime.date | None, datetime.time | None]:
    """从中文文本中提取日期和时间

    Returns:
        (date, time) 元组，未识别到的为 None
    """
    today = get_date_context().today
    date = None
    time = None

    # 尝试匹配 "X月X日" 或 "X月X号"
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year
        date = datetime.date(year, month, day)
        if date < today:
            date = datetime.date(year + 1, month, day)

    # 尝试匹配时间 "XX:XX" 或 "X点X分" 或 "下午X点"
    m = re.search(r'(\d{1,2}):(\d{2})', text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        time = datetime.time(hour, minute)
    else:
        m = re.search(r'(上午|下午|晚上|中午|早上)?\s*(\d{1,2})\s*[点时]\s*(\d{1,2})?\s*分?', text)
        if m:
            period = m.group(1) or ''
            hour = int(m.group(2))
            minute = int(m.group(3)) if m.group(3) else 0
            if '下午' in period or '晚上' in period:
                if hour < 12:
                    hour += 12
            elif '中午' in period:
                if hour < 12:
                    hour += 12
            elif '上午' in period or '早上' in period:
                pass  # 保持原值
            time = datetime.time(hour, minute)

    return date, time


def format_remaining_time(schedule_date: datetime.date | None, schedule_time: datetime.time = None) -> str:
    """格式化距离日程的剩余时间"""
    if not schedule_date:
        return '未设日期'

    now = get_date_context().now.replace(tzinfo=None)

    if schedule_time:
        target = datetime.datetime.combine(schedule_date, schedule_time)
    else:
        target = datetime.datetime.combine(schedule_date, datetime.time(23, 59))

    diff = target - now
    total_seconds = diff.total_seconds()

    if total_seconds < 0:
        return '已过期'
    elif total_seconds < 3600:
        minutes = int(total_seconds // 60)
        return f'还有{minutes}分钟'
    elif total_seconds < 86400:
        hours = int(total_seconds // 3600)
        return f'还有{hours}小时'
    elif total_seconds < 259200:
        days = int(total_seconds // 86400)
        return f'还有{days}天'
    else:
        days = int(total_seconds // 86400)
        weeks = days // 7
        if weeks > 0:
            return f'还有{weeks}周'
        return f'还有{days}天'


def format_schedule_time(s: 'Schedule') -> str:
    """格式化日程时间为可读字符串"""
    from db.models import Schedule
    parts = []
    if s.date:
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        wd = weekday_names[s.date.weekday()]
        parts.append(f'{s.date.isoformat()} ({wd})')
    if s.start_time:
        parts.append(s.start_time.strftime('%H:%M'))
    if s.end_time:
        parts.append(f'~{s.end_time.strftime("%H:%M")}')
    return ' '.join(parts)
