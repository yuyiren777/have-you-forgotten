"""日程解析引擎 — 将模型输出的 JSON 转为数据库记录"""
import datetime
import re
from typing import Optional
from utils.date_parser import parse_relative_date, resolve_unspecified_year_date
from utils.schedule_content import clean_optional_text, readable_notes


def _normalize_unspecified_year(
    parsed: datetime.date, item: dict, today: datetime.date
) -> datetime.date:
    """Correct model dates when the original source stated only month and day."""
    explicit_year = item.get("date_year_explicit")
    if explicit_year is False or (explicit_year is None and parsed.year < today.year):
        corrected = resolve_unspecified_year_date(parsed.month, parsed.day, today)
        if corrected:
            return corrected
    return parsed


def _parse_time(value) -> datetime.time | None:
    """Parse a model clock value strictly instead of accepting malformed tails."""
    if value is None or str(value).strip().lower() in ("", "none", "null"):
        return None
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", str(value).strip())
    if not match:
        return None
    try:
        return datetime.time(*(int(part or 0) for part in match.groups()))
    except ValueError:
        return None


def parse_schedule_item(item: dict, today: datetime.date = None) -> Optional[dict]:
    """解析单条日程，归一化日期时间

    Args:
        item: 模型输出的单条日程 dict
        today: 今天日期

    Returns:
        解析后的 dict，可直接用于创建 Schedule；解析失败返回 None
    """
    if today is None:
        today = datetime.date.today()

    if not item.get('title'):
        return None

    description = clean_optional_text(item.get('description'))
    result = {
        'title': str(item.get('title', '')).strip(),
        'description': description or None,
        'date': None,
        'start_time': None,
        'end_time': None,
        'location': clean_optional_text(item.get('location')) or None,
        'notes': readable_notes(item.get('notes')) or description or None,
        'repeat_rule': None,
        'urgency': 0,
    }

    # 解析日期
    date_str = item.get('date', '')
    if date_str and date_str != 'null' and str(date_str).lower() != 'none':
        try:
            # 尝试解析 YYYY-MM-DD
            if isinstance(date_str, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_str.strip()):
                parsed = datetime.date.fromisoformat(date_str.strip())
                result['date'] = _normalize_unspecified_year(parsed, item, today)
            elif isinstance(date_str, str) and (match := re.fullmatch(r'(\d{1,2})[-/](\d{1,2})', date_str.strip())):
                result['date'] = resolve_unspecified_year_date(
                    int(match.group(1)), int(match.group(2)), today
                )
            else:
                parsed = parse_relative_date(str(date_str), today)
                if parsed:
                    result['date'] = parsed
        except Exception:
            # 尝试用相对日期解析
            try:
                parsed = parse_relative_date(str(date_str), today)
                if parsed:
                    result['date'] = parsed
            except Exception:
                pass

    # 解析时间
    result['start_time'] = _parse_time(item.get('start_time'))
    result['end_time'] = _parse_time(item.get('end_time'))

    # 解析重复规则
    repeat = item.get('repeat', 'none')
    if repeat and str(repeat) not in ('none', 'None', '', 'null'):
        result['repeat_rule'] = str(repeat)

    # 解析紧急程度
    urgency_map = {'normal': 0, 'important': 1, 'urgent': 2}
    result['urgency'] = urgency_map.get(str(item.get('urgency', 'normal')), 0)

    return result


def parse_schedule_list(items: list[dict], today: datetime.date = None) -> list[dict]:
    """解析日程列表

    Returns:
        解析成功的结果列表
    """
    results = []
    for item in items:
        parsed = parse_schedule_item(item, today)
        if parsed:
            results.append(parsed)
    return results
