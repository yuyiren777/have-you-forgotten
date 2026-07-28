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


def _get_advance_minutes() -> int:
    """Return the persisted day/hour/minute advance as total minutes."""
    from db.models import Config
    try:
        values = {}
        for key in ('reminder_advance_days', 'reminder_advance_hours', 'reminder_advance_minutes'):
            row = Config.get_or_none(Config.key == key)
            if row is not None:
                try:
                    values[key] = max(0, int(row.value))
                except (TypeError, ValueError):
                    values[key] = 0
        if values:
            return (
                values.get('reminder_advance_days', 0) * 24 * 60
                + values.get('reminder_advance_hours', 0) * 60
                + values.get('reminder_advance_minutes', 0)
            )

        row = Config.get_or_none(Config.key == 'reminder_advance')
        if row is not None:
            return max(0, int(row.value))
    except Exception:
        pass
    return 30


def _check_and_remind():
    """检查日程并发送提醒（由 APScheduler 每分钟调用一次）"""
    now = datetime.datetime.now()
    today = now.date()
    advance = _get_advance_minutes()

    # 1. 查找需要提醒的日程
    pending_schedules = Schedule.select().where(
        Schedule.status == 'pending'
    ).order_by(Schedule.date.asc(), Schedule.start_time.asc())

    for s in pending_schedules:
        should_remind = False
        reason = ''

        if not s.date:
            continue

        # Timed and all-day schedules share one advance rule. An all-day item
        # starts at 00:00 on its date, so long lead times also work for it.
        target = datetime.datetime.combine(s.date, s.start_time or datetime.time.min)
        diff_minutes = (target - now).total_seconds() / 60

        if advance > 0 and 0 < diff_minutes <= advance:
            should_remind = True
            reason = f'还有 {max(1, int(diff_minutes))} 分钟'
        elif s.start_time and s.urgency >= 2 and 0 < diff_minutes <= 120:
            # Urgent timed schedules retain the two-hour fallback reminder.
            should_remind = True
            reason = f'（紧急）还有 {max(1, int(diff_minutes))} 分钟'
        elif not s.start_time and s.date == today and now.hour >= 22:
            # Keep the existing end-of-day expiration behavior for all-day items.
            s.status = 'expired'
            s.save()
            continue

        if not should_remind:
            continue

        # 2. 发送提醒
        title = f'⏰ 日程提醒: {s.title}'
        formatted = format_schedule_time(s)
        remaining = format_remaining_time(s.date, s.start_time)

        content_lines = [
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
            method='wechat',
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
        email_ok = _send_email(f'⏰ 日程提醒 — {s.title}', email_html)
        ReminderLog.create(
            schedule=s,
            method='email',
            status='sent' if email_ok else 'failed',
            message=content,
        )

        # Windows 通知日志
        ReminderLog.create(
            schedule=s,
            method='windows',
            status='sent',
            message=content,
        )

        # 更新状态
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
