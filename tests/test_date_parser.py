import datetime
from types import SimpleNamespace

from utils.date_parser import (
    format_remaining_time,
    format_schedule_time,
    parse_relative_date,
)


def test_remaining_time_handles_missing_date():
    assert format_remaining_time(None) == '未设日期'


def test_yearless_month_day_uses_nearest_non_past_occurrence():
    assert parse_relative_date("12月30日", datetime.date(2026, 7, 28)) == datetime.date(2026, 12, 30)
    assert parse_relative_date("1月1日", datetime.date(2026, 12, 30)) == datetime.date(2027, 1, 1)


def test_invalid_calendar_date_is_rejected_instead_of_clamped():
    assert parse_relative_date("2026-02-30", datetime.date(2026, 1, 1)) is None
    assert parse_relative_date("下个月31号", datetime.date(2026, 1, 15)) is None
    assert parse_relative_date("3天之后多余文字", datetime.date(2026, 1, 15)) is None


def test_chinese_day_number_above_twelve_is_not_changed_to_first_day():
    assert parse_relative_date("下个月二十一号", datetime.date(2026, 7, 28)) == datetime.date(2026, 8, 21)


def test_remaining_time_has_clear_boundaries():
    now = datetime.datetime(2026, 7, 28, 9, 0, 0)
    assert format_remaining_time(datetime.date(2026, 7, 28), datetime.time(9, 0), now) == "现在"
    assert format_remaining_time(datetime.date(2026, 7, 28), datetime.time(9, 0, 30), now) == "不到1分钟"
    assert format_remaining_time(datetime.date(2026, 7, 28), datetime.time(8, 58), now) == "已开始2分钟"
    assert format_remaining_time(datetime.date(2026, 7, 28), None, now) == "还有3小时"
    assert format_remaining_time(
        datetime.date(2026, 7, 28),
        None,
        datetime.datetime(2026, 7, 28, 13, 0),
    ) == "已开始60分钟"


def test_date_only_schedule_displays_the_noon_default():
    schedule = SimpleNamespace(
        date=datetime.date(2026, 8, 2),
        start_time=None,
        end_time=None,
    )

    assert format_schedule_time(schedule).endswith("12:00（默认）")
