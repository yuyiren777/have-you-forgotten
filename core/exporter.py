"""Local schedule export to iCalendar and CSV."""

from __future__ import annotations

import csv
import datetime
import io
import os
from pathlib import Path

from utils.date_parser import DEFAULT_DATE_ONLY_TIME
from utils.schedule_content import clean_optional_text, readable_notes


STATUS_NAMES = {
    "pending": "待处理",
    "reminded": "已提醒",
    "completed": "已完成",
    "expired": "已过期",
}
URGENCY_NAMES = {0: "普通", 1: "重要", 2: "紧急"}
WEEKDAYS = {1: "MO", 2: "TU", 3: "WE", 4: "TH", 5: "FR", 6: "SA", 7: "SU"}


def _ics_escape(value) -> str:
    text = clean_optional_text(value)
    return (
        text.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_ics_line(line: str) -> list[str]:
    """Fold a content line without splitting a UTF-8 character."""
    lines = []
    current = ""
    limit = 75
    for character in line:
        candidate = current + character
        if current and len(candidate.encode("utf-8")) > limit:
            lines.append(current)
            current = " " + character
            limit = 75
        else:
            current = candidate
    lines.append(current)
    return lines


def _description(schedule) -> str:
    description = clean_optional_text(schedule.description)
    notes = readable_notes(schedule.notes)
    if notes and notes != description:
        return f"{description}\n备注：{notes}" if description else f"备注：{notes}"
    return description


def _rrule(repeat_rule) -> str:
    rule = clean_optional_text(repeat_rule)
    if rule == "daily":
        return "FREQ=DAILY"
    if rule.startswith("weekly:"):
        days = [WEEKDAYS.get(int(day)) for day in rule.split(":", 1)[1].split(",") if day.isdigit()]
        days = [day for day in days if day]
        return f"FREQ=WEEKLY;BYDAY={','.join(days)}" if days else ""
    if rule.startswith("monthly:"):
        day = rule.split(":", 1)[1]
        return f"FREQ=MONTHLY;BYMONTHDAY={day}" if day.isdigit() else ""
    return ""


def _calendar_times(schedule) -> tuple[datetime.datetime, datetime.datetime]:
    start_time = schedule.start_time or DEFAULT_DATE_ONLY_TIME
    start = datetime.datetime.combine(schedule.date, start_time)
    if schedule.end_time is None:
        return start, start + datetime.timedelta(hours=1)
    end = datetime.datetime.combine(schedule.date, schedule.end_time)
    if schedule.end_time < start_time:
        end += datetime.timedelta(days=1)
    elif end == start:
        end += datetime.timedelta(hours=1)
    return start, end


def render_ics(schedules, now: datetime.datetime | None = None) -> str:
    """Render schedules as RFC 5545-compatible calendar text."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp = now.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Have You Forgotten//AI Memo//ZH-CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:AI备忘录日程",
    ]
    for schedule in schedules:
        component = "VEVENT" if schedule.date else "VTODO"
        raw_lines.extend([
            f"BEGIN:{component}",
            f"UID:schedule-{schedule.id}@have-you-forgotten.local",
            f"DTSTAMP:{stamp}",
            f"SUMMARY:{_ics_escape(schedule.title)}",
        ])
        description = _description(schedule)
        location = clean_optional_text(schedule.location)
        if description:
            raw_lines.append(f"DESCRIPTION:{_ics_escape(description)}")
        if location:
            raw_lines.append(f"LOCATION:{_ics_escape(location)}")
        raw_lines.append(f"PRIORITY:{1 if schedule.urgency == 2 else 5 if schedule.urgency == 1 else 0}")
        raw_lines.append(f"X-AI-MEMO-STATUS:{_ics_escape(STATUS_NAMES.get(schedule.status, schedule.status))}")

        if schedule.date:
            start, end = _calendar_times(schedule)
            raw_lines.append(f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}")
            raw_lines.append(f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}")
            recurrence = _rrule(schedule.repeat_rule)
            if recurrence:
                raw_lines.append(f"RRULE:{recurrence}")
            raw_lines.append("STATUS:CONFIRMED")
        else:
            raw_lines.append(
                "STATUS:COMPLETED" if schedule.status == "completed" else "STATUS:NEEDS-ACTION"
            )
        raw_lines.append(f"END:{component}")
    raw_lines.append("END:VCALENDAR")
    return "\r\n".join(
        folded for line in raw_lines for folded in _fold_ics_line(line)
    ) + "\r\n"


def render_csv(schedules) -> str:
    """Render schedules as a Chinese-column CSV document."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "标题", "日期", "开始时间", "结束时间", "地点", "备注",
        "紧急度", "状态", "重复规则",
    ])
    for schedule in schedules:
        writer.writerow([
            clean_optional_text(schedule.title),
            schedule.date.isoformat() if schedule.date else "",
            schedule.start_time.strftime("%H:%M") if schedule.start_time else (
                "12:00（默认）" if schedule.date else ""
            ),
            schedule.end_time.strftime("%H:%M") if schedule.end_time else "",
            clean_optional_text(schedule.location),
            readable_notes(schedule.notes) or clean_optional_text(schedule.description),
            URGENCY_NAMES.get(schedule.urgency, "普通"),
            STATUS_NAMES.get(schedule.status, schedule.status),
            clean_optional_text(schedule.repeat_rule),
        ])
    return output.getvalue()


def export_schedules(schedules, file_path: str, export_format: str) -> None:
    """Write an export atomically so failures cannot leave a partial file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        if export_format == "ics":
            temporary.write_bytes(render_ics(schedules).encode("utf-8"))
        elif export_format == "csv":
            temporary.write_bytes(("\ufeff" + render_csv(schedules)).encode("utf-8"))
        else:
            raise ValueError(f"不支持的导出格式：{export_format}")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
