"""提醒调度服务 — APScheduler 定时扫描 + 多通道推送"""
import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from db.database import get_db
from db.models import Schedule, ReminderLog
from core.api_client import get_push_config
from utils.date_parser import format_remaining_time, format_schedule_time

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# 回调函数（由 GUI 层设置）
on_windows_notify = None  # callable(title, message)
on_alert_tray = None      # callable()


def _send_wechat(title: str, content: str) -> bool:
    """发送微信推送"""
    config = get_push_config()
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


def _send_email(subject: str, html_content: str) -> bool:
    """发送邮件"""
    config = get_push_config()
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


def _config_minutes(config, prefix: str) -> int | None:
    """Read a day/hour/minute triplet, returning None when it was never saved."""
    values = []
    found = False
    for unit in ('days', 'hours', 'minutes'):
        row = config.get_or_none(config.key == f'{prefix}_{unit}')
        if row is not None:
            found = True
            try:
                values.append(max(0, int(row.value)))
            except (TypeError, ValueError):
                values.append(0)
        else:
            values.append(0)
    if not found:
        return None
    return values[0] * 24 * 60 + values[1] * 60 + values[2]


def _get_reminder_stages() -> list[tuple[str, str, int]]:
    """Return enabled reminder stages in chronological order."""
    from db.models import Config
    try:
        final = _config_minutes(Config, 'reminder_final')
        if final is None:
            # Migrate the previous single-stage configuration at read time.
            final = _config_minutes(Config, 'reminder_advance')
            if final is None:
                row = Config.get_or_none(Config.key == 'reminder_advance')
                final = max(0, int(row.value)) if row is not None else 30

        first = _config_minutes(Config, 'reminder_first') or 0
        second = _config_minutes(Config, 'reminder_second') or 0
        stages = []
        if first > 0:
            stages.append(('first', '第一次提醒', first))
        if second > 0:
            stages.append(('second', '第二次提醒', second))
        if final > 0:
            stages.append(('final', '最后提醒', final))
        return stages
    except Exception:
        return [('final', '最后提醒', 30)]


def _select_due_stage(diff_minutes: float, stages, sent_stages: set[str]):
    """Select the closest unhandled lead time that has become due.

    Choosing the smallest eligible lead prevents several missed early stages
    from firing together when the app is opened close to the event.
    """
    candidates = [
        stage for stage in stages
        if stage[0] not in sent_stages and 0 < diff_minutes <= stage[2]
    ]
    return min(candidates, key=lambda stage: stage[2]) if candidates else None


def _check_and_remind():
    """检查日程并发送提醒（由 APScheduler 每分钟调用一次）"""
    now = datetime.datetime.now()
    today = now.date()
    stages = _get_reminder_stages()

    # 1. 查找需要提醒的日程
    pending_schedules = Schedule.select().where(
        Schedule.status == 'pending'
    ).order_by(Schedule.date.asc(), Schedule.start_time.asc())

    for s in pending_schedules:
        if not s.date:
            continue

        # Timed and all-day schedules share one advance rule. An all-day item
        # starts at 00:00 on its date, so long lead times also work for it.
        target = datetime.datetime.combine(s.date, s.start_time or datetime.time.min)
        diff_minutes = (target - now).total_seconds() / 60

        if not s.start_time and s.date == today and now.hour >= 22:
            # Keep the existing end-of-day expiration behavior for all-day items.
            s.status = 'expired'
            s.save()
            continue

        sent_stage_rows = ReminderLog.select().where(
            (ReminderLog.schedule == s) & ReminderLog.method.startswith('windows:')
        )
        sent_stages = {row.method.split(':', 1)[1] for row in sent_stage_rows}
        stage = _select_due_stage(diff_minutes, stages, sent_stages)
        if stage is None:
            continue
        stage_key, stage_label, _ = stage

        # 2. 发送提醒
        title = f'⏰ {stage_label}: {s.title}'
        formatted = format_schedule_time(s)
        remaining = format_remaining_time(s.date, s.start_time)

        content_lines = [
            f'🔔 {stage_label}',
            f'📌 {s.title}',
            f'📅 {formatted}',
        ]
        if s.location:
            content_lines.append(f'📍 {s.location}')
        content_lines.append(f'⏳ {remaining}')
        if s.notes:
            content_lines.append(f'📝 {s.notes}')

        content = '\n'.join(content_lines)

        # Windows 通知
        if on_windows_notify:
            try:
                on_windows_notify(title, content)
            except Exception as e:
                logger.warning(f'Windows 通知失败: {e}')

        # 微信推送
        wechat_ok = _send_wechat(title, content)
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
            location=s.location or '',
            notes=s.notes or '',
            remaining=remaining,
        )
        email_ok = _send_email(f'⏰ {stage_label} — {s.title}', email_html)
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

    # 3. 清理过期日程（超过 3 天未处理的标记为 expired）
    three_days_ago = today - datetime.timedelta(days=3)
    Schedule.update(status='expired').where(
        (Schedule.status == 'pending') &
        (Schedule.date < three_days_ago)
    ).execute()


def _remind_undated_on_start():
    """Show each undated pending item once when this app session starts."""
    undated_schedules = Schedule.select().where(
        (Schedule.status == 'pending') & Schedule.date.is_null(True)
    )

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
