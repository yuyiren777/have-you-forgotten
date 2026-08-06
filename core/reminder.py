"""提醒调度服务 — APScheduler 定时扫描 + 多通道推送"""
import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from db.database import get_db
from db.models import Schedule, ReminderLog
from core.api_client import get_push_config
from utils.date_parser import (
    DEFAULT_DATE_ONLY_TIME,
    format_remaining_time,
    format_schedule_time,
)
from utils.schedule_content import clean_optional_text, readable_notes

logger = logging.getLogger(__name__)

LOCAL_TIMEZONE = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
scheduler = BackgroundScheduler(timezone=LOCAL_TIMEZONE)
POST_START_GRACE_MINUTES = 60
ALL_DAY_REMINDER_DEADLINE = datetime.time(22, 0)

# 回调函数（由 GUI 层设置）
on_windows_notify = None  # callable(title, message)
on_alert_tray = None      # callable()


def _send_wechat(title: str, content: str, config: dict | None = None) -> bool:
    """发送微信推送"""
    config = config or get_push_config()
    service = config.get('wechat_service', 'none')

    if service == 'serverchan':
        from push.serverchan import send
        return send(config.get('wechat_token', ''), title, content)[0]
    elif service == 'pushplus':
        from push.pushplus import send
        return send(config.get('wechat_token', ''), title, content)[0]
    elif service == 'wxpusher':
        from push.wxpusher import send
        uid = config.get('wechat_token', '')  # wxpusher 的 token 实际存的是 uid
        return send(config.get('wechat_app_token', ''), uid, title, content)[0]

    return False


def _send_email(subject: str, html_content: str, config: dict | None = None) -> bool:
    """发送邮件"""
    config = config or get_push_config()
    service = config.get('email_service', 'none')
    if service == 'none':
        return False

    from push.email_sender import send
    return send(
        service=service,
        email_address=config.get('email_address', ''),
        email_password=config.get('email_password', ''),
        to_address=config.get('email_address', ''),  # 默认发给自己
        subject=subject,
        html_content=html_content,
        custom_host=config.get('email_smtp_host', ''),
        custom_port=int(config.get('email_smtp_port', '0')),
    )[0]


def _config_minutes(values: dict[str, str], prefix: str) -> int | None:
    """Read a day/hour/minute triplet, returning None when it was never saved."""
    parts = []
    found = False
    for unit in ('days', 'hours', 'minutes'):
        key = f'{prefix}_{unit}'
        if key in values:
            found = True
            try:
                parts.append(max(0, int(values[key])))
            except (TypeError, ValueError):
                parts.append(0)
        else:
            parts.append(0)
    if not found:
        return None
    return parts[0] * 24 * 60 + parts[1] * 60 + parts[2]


def _get_reminder_stages() -> list[tuple[str, str, int]]:
    """Return enabled reminder stages in chronological order."""
    from db.models import Config
    try:
        prefixes = ('reminder_final', 'reminder_first', 'reminder_second', 'reminder_advance')
        keys = {
            f'{prefix}_{unit}'
            for prefix in prefixes
            for unit in ('days', 'hours', 'minutes')
        }
        keys.add('reminder_advance')
        values = {
            row.key: row.value
            for row in Config.select().where(Config.key.in_(tuple(keys)))
        }
        final = _config_minutes(values, 'reminder_final')
        if final is None:
            # Migrate the previous single-stage configuration at read time.
            final = _config_minutes(values, 'reminder_advance')
            if final is None:
                legacy_value = values.get('reminder_advance')
                final = max(0, int(legacy_value)) if legacy_value is not None else 30

        final = final if final and final > 0 else 30
        first = _config_minutes(values, 'reminder_first') or 0
        second = _config_minutes(values, 'reminder_second') or 0
        stages = [('final', '最后提醒', final)]
        if second > final:
            stages.append(('second', '第二次提醒', second))
        if first > max(final, second):
            stages.append(('first', '第一次提醒', first))
        return sorted(stages, key=lambda stage: stage[2], reverse=True)
    except Exception:
        return [('final', '最后提醒', 30)]


def _select_due_stage(diff_minutes: float, stages, sent_stages: set[str]):
    """Select the closest unhandled lead time that has become due.

    Choosing the smallest eligible lead prevents several missed early stages
    from firing together when the app is opened close to the event.
    """
    candidates = [
        stage for stage in stages
        if stage[0] not in sent_stages and diff_minutes <= stage[2]
    ]
    return min(candidates, key=lambda stage: stage[2]) if candidates else None


def _skipped_stage_keys(stage, stages, handled_stages: set[str]) -> list[str]:
    """Return earlier reminders that must never be replayed after this stage."""
    if stage is None:
        return []
    selected_lead = stage[2]
    return [
        key for key, _label, lead in stages
        if lead > selected_lead and key not in handled_stages
    ]


def _schedule_reminder_window(
    schedule_date: datetime.date,
    start_time: datetime.time | None,
    end_time: datetime.time | None,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Return the event target and the last useful instant for a local reminder."""
    if start_time is None:
        target = datetime.datetime.combine(schedule_date, DEFAULT_DATE_ONLY_TIME)
        deadline = datetime.datetime.combine(schedule_date, ALL_DAY_REMINDER_DEADLINE)
        return target, deadline

    target = datetime.datetime.combine(schedule_date, start_time)
    if end_time is None:
        return target, target + datetime.timedelta(minutes=POST_START_GRACE_MINUTES)

    deadline = datetime.datetime.combine(schedule_date, end_time)
    if end_time < start_time:
        deadline += datetime.timedelta(days=1)
    elif end_time == start_time:
        deadline = target + datetime.timedelta(minutes=POST_START_GRACE_MINUTES)
    return target, deadline


def _is_schedule_expired(schedule, now: datetime.datetime | None = None) -> bool:
    """Return whether a dated, unfinished occurrence has passed its useful window."""
    if not schedule.date:
        return False
    now = now or datetime.datetime.now()
    _target, deadline = _schedule_reminder_window(
        schedule.date,
        schedule.start_time,
        schedule.end_time,
    )
    return now >= deadline


def refresh_expired_schedule_statuses(now: datetime.datetime | None = None) -> int:
    """Persist real-time expiration for dated, unfinished schedules.

    Reminder history must not depend on whether a notification happened to be
    delivered. A pending or reminded schedule becomes expired when its event
    window ends; completed and undated schedules are deliberately untouched.
    """
    now = now or datetime.datetime.now()
    get_db()
    candidates = Schedule.select().where(
        (Schedule.status.in_(("pending", "reminded")))
        & Schedule.date.is_null(False)
    )
    expired_ids = [
        schedule.id for schedule in candidates
        if _is_schedule_expired(schedule, now)
    ]
    if not expired_ids:
        return 0
    return Schedule.update(status="expired", updated_at=now).where(
        Schedule.id.in_(expired_ids)
    ).execute()


def _build_reminder_text(schedule, stage_label: str):
    """Build plain Chinese reminder text without exposing stored JSON."""
    title = f'{stage_label}：{schedule.title}'
    formatted = format_schedule_time(schedule)
    remaining = format_remaining_time(schedule.date, schedule.start_time)
    location = clean_optional_text(schedule.location)
    notes = readable_notes(schedule.notes)
    content = '\n'.join([
        f'提醒阶段：{stage_label}',
        f'日程：{schedule.title}',
        f'时间：{formatted}',
        f'地点：{location or "未填写"}',
        f'剩余时间：{remaining}',
        f'备注：{notes or "未填写"}',
    ])
    return title, content, formatted, remaining, location, notes


def _check_and_remind():
    """检查日程并发送提醒（由 APScheduler 每分钟调用一次）"""
    now = datetime.datetime.now()
    today = now.date()
    stages = _get_reminder_stages()

    # Keep lifecycle states current even when the final reminder was sent long
    # ago. This also covers schedules that did not have a usable notification.
    refresh_expired_schedule_statuses(now)

    # 1. 查找需要提醒的日程
    pending_schedules = list(Schedule.select().where(
        Schedule.status == 'pending'
    ).order_by(Schedule.date.asc(), Schedule.start_time.asc()))

    sent_stages_by_schedule: dict[int, set[str]] = {
        schedule.id: set() for schedule in pending_schedules
    }
    schedule_ids = tuple(sent_stages_by_schedule)
    if schedule_ids:
        sent_stage_rows = ReminderLog.select(
            ReminderLog.schedule, ReminderLog.method
        ).where(
            (ReminderLog.schedule.in_(schedule_ids))
            & ReminderLog.method.startswith('windows:')
        )
        for row in sent_stage_rows:
            sent_stages_by_schedule.setdefault(row.schedule_id, set()).add(
                row.method.split(':', 1)[1]
            )

    push_config = None

    for s in pending_schedules:
        if not s.date:
            continue

        target, deadline = _schedule_reminder_window(s.date, s.start_time, s.end_time)
        diff_minutes = (target - now).total_seconds() / 60

        if now >= deadline:
            if not s.start_time and s.date == today:
                # Keep the existing end-of-day expiration behavior for all-day items.
                s.status = 'expired'
                s.save()
            continue

        sent_stages = sent_stages_by_schedule.get(s.id, set())
        stage = _select_due_stage(diff_minutes, stages, sent_stages)
        if stage is None:
            continue
        stage_key, stage_label, _ = stage

        for skipped_key in _skipped_stage_keys(stage, stages, sent_stages):
            ReminderLog.create(
                schedule=s,
                method=f'windows:{skipped_key}',
                status='skipped',
                message=f'已错过该提醒阶段，改为发送 {stage_label}',
            )

        # 2. 发送提醒
        title, content, formatted, remaining, location, notes = _build_reminder_text(
            s, stage_label
        )

        # Windows 通知
        if on_windows_notify:
            try:
                on_windows_notify(title, content)
            except Exception as e:
                logger.warning(f'Windows 通知失败: {e}')

        # One scan uses one configuration snapshot for all external channels.
        if push_config is None:
            push_config = get_push_config()

        # 微信推送
        wechat_ok = _send_wechat(title, content, push_config)
        ReminderLog.create(
            schedule=s,
            method=f'wechat:{stage_key}',
            status='sent' if wechat_ok else 'failed',
            message=content,
        )

        # 邮件推送
        from push.email_sender import build_schedule_email
        email_html = build_schedule_email(
            title=s.title,
            date_str=formatted,
            location=location,
            notes=notes or '未填写',
            remaining=remaining,
        )
        email_ok = _send_email(f'{stage_label}：{s.title}', email_html, push_config)
        ReminderLog.create(
            schedule=s,
            method=f'email:{stage_key}',
            status='sent' if email_ok else 'failed',
            message=content,
        )

        # Windows 通知日志
        ReminderLog.create(
            schedule=s,
            method=f'windows:{stage_key}',
            status='sent',
            message=content,
        )

        # Early stages must not suppress the remaining reminders.
        if stage_key == 'final':
            s.status = 'reminded'
            s.reminded_at = now
            s.save()

        # 托盘闪烁
        if on_alert_tray:
            try:
                on_alert_tray()
            except Exception:
                pass

def _remind_undated_on_start():
    """Show each undated pending item once when this app session starts."""
    undated_schedules = list(Schedule.select().where(
        (Schedule.status == 'pending') & Schedule.date.is_null(True)
    ))

    for schedule in undated_schedules:
        title = f'未设日期待办: {schedule.title}'
        content = f'{schedule.title}\n该日程未设置日期，已在应用启动时提醒。'
        if on_windows_notify:
            try:
                on_windows_notify(title, content)
            except Exception as e:
                logger.warning(f'启动提醒显示失败: {e}')

        ReminderLog.create(
            schedule=schedule,
            method='windows',
            status='sent',
            message=content,
        )

    if undated_schedules and on_alert_tray:
        try:
            on_alert_tray()
        except Exception:
            pass


def start_reminder_service():
    """启动提醒服务"""
    if scheduler.running:
        return
    scheduler.add_job(
        _check_and_remind,
        'interval',
        seconds=60,
        id='reminder_check',
        replace_existing=True,
    )
    scheduler.add_job(
        _remind_undated_on_start,
        'date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=1),
        id='undated_start_reminder',
        replace_existing=True,
        misfire_grace_time=30,
    )
    scheduler.start()
    logger.info('提醒服务已启动（每 60 秒扫描一次）')


def stop_reminder_service():
    """停止提醒服务"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info('提醒服务已停止')


def mark_completed(schedule_id: int):
    """标记日程为已完成"""
    Schedule.update(status='completed').where(Schedule.id == schedule_id).execute()


def mark_pending(schedule_id: int):
    """标记日程为待处理"""
    Schedule.update(status='pending').where(Schedule.id == schedule_id).execute()
