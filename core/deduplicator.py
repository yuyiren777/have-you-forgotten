"""日程查重合并 — 避免重复入库"""
from db.models import Schedule


def find_duplicate(schedule_data: dict) -> Schedule | None:
    """检查是否有重复日程

    规则：同一天 + 标题相同 + 开始时间完全相同。

    相差几分钟的安排可能是独立日程，不能按时间邻近合并。

    Args:
        schedule_data: 待入库的日程 dict
        threshold_minutes: 视为重复的时间差（分钟）

    Returns:
        如果找到重复，返回已有的 Schedule 对象；否则返回 None
    """
    title = schedule_data.get('title', '')
    date = schedule_data.get('date')
    start_time = schedule_data.get('start_time')

    if not title or not date:
        return None

    # 查询同一天、同标题的日程
    candidates = Schedule.select().where(
        (Schedule.title == title) &
        (Schedule.date == date)
    )

    for existing in candidates:
        # 都没有具体时间 → 视为重复
        if not start_time and not existing.start_time:
            return existing

        # 都有具体时间时，只有完全相同才视为重复。
        if start_time and existing.start_time:
            if start_time == existing.start_time:
                return existing

        # 一个有时间、一个没有时间，保留为两条独立日程。

    return None


def merge_schedule(existing: Schedule, new_data: dict):
    """合并日程：用新数据更新已有记录"""
    updated = False

    if new_data.get('description') and not existing.description:
        existing.description = new_data['description']
        updated = True

    if new_data.get('end_time') and not existing.end_time:
        existing.end_time = new_data['end_time']
        updated = True

    if new_data.get('location') and not existing.location:
        existing.location = new_data['location']
        updated = True

    if new_data.get('notes') and not existing.notes:
        existing.notes = new_data['notes']
        updated = True

    if new_data.get('repeat_rule') and not existing.repeat_rule:
        existing.repeat_rule = new_data['repeat_rule']
        updated = True

    if new_data.get('urgency', 0) > existing.urgency:
        existing.urgency = new_data['urgency']
        updated = True

    if updated:
        import datetime
        existing.updated_at = datetime.datetime.now()
        existing.save()

    return existing
