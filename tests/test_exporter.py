import csv
import datetime
import io
from types import SimpleNamespace

from core.exporter import export_schedules, render_csv, render_ics


def _schedule(**overrides):
    values = {
        "id": 7,
        "title": "复习数学,第二章",
        "description": "完成习题",
        "date": datetime.date(2026, 8, 3),
        "start_time": None,
        "end_time": None,
        "location": "自习室;A",
        "notes": '{"description":"带计算器"}',
        "repeat_rule": "weekly:1,3",
        "urgency": 2,
        "status": "pending",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_ics_exports_date_only_schedule_at_noon_with_recurrence():
    content = render_ics(
        [_schedule()],
        now=datetime.datetime(2026, 8, 2, tzinfo=datetime.timezone.utc),
    )

    assert "DTSTART:20260803T120000\r\n" in content
    assert "DTEND:20260803T130000\r\n" in content
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO,WE\r\n" in content
    assert "SUMMARY:复习数学\\,第二章" in content
    assert "LOCATION:自习室\\;A" in content


def test_ics_keeps_undated_schedule_as_todo():
    content = render_ics(
        [_schedule(date=None, status="completed")],
        now=datetime.datetime(2026, 8, 2, tzinfo=datetime.timezone.utc),
    )

    assert "BEGIN:VTODO" in content
    assert "STATUS:COMPLETED" in content
    assert "DTSTART" not in content


def test_csv_uses_chinese_columns_and_readable_notes():
    rows = list(csv.reader(io.StringIO(render_csv([_schedule()]))))

    assert rows[0][:4] == ["标题", "日期", "开始时间", "结束时间"]
    assert rows[1][2] == "12:00（默认）"
    assert rows[1][5] == "带计算器"
    assert rows[1][6:8] == ["紧急", "待处理"]


def test_csv_file_has_utf8_bom_for_excel(tmp_path):
    target = tmp_path / "日程.csv"

    export_schedules([_schedule()], str(target), "csv")

    assert target.read_bytes().startswith(b"\xef\xbb\xbf")
