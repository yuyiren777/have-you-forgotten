"""日程解析引擎 — 将模型输出的 JSON 转为数据库记录"""
import datetime
import json
import re
from typing import Optional
from utils.date_parser import parse_relative_date


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

    result = {
        'title': str(item.get('title', '')).strip(),
        'description': str(item.get('description', '')).strip() or None,
        'date': None,
        'start_time': None,
        'end_time': None,
        'location': str(item.get('location', '')).strip() or None,
        'notes': json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else None,
        'repeat_rule': None,
        'urgency': 0,
    }

    # 解析日期
    date_str = item.get('date', '')
    if date_str and date_str != 'null' and str(date_str).lower() != 'none':
        try:
            # 尝试解析 YYYY-MM-DD
            if isinstance(date_str, str) and re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                result['date'] = datetime.date.fromisoformat(date_str)
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
    start = item.get('start_time', '')
    if start and str(start) not in ('null', 'None', ''):
        try:
            if isinstance(start, str):
                parts = start.strip().split(':')
                if len(parts) >= 2:
                    result['start_time'] = datetime.time(int(parts[0]), int(parts[1]))
        except Exception:
            pass

    end = item.get('end_time', '')
    if end and str(end) not in ('null', 'None', ''):
        try:
            if isinstance(end, str):
                parts = end.strip().split(':')
                if len(parts) >= 2:
                    result['end_time'] = datetime.time(int(parts[0]), int(parts[1]))
        except Exception:
            pass

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
