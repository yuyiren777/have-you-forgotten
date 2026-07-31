import datetime

from core.parser import parse_schedule_item
from core.workflow import parse_model_response
from utils.date_parser import resolve_unspecified_year_date


def test_yearless_model_date_corrects_a_hallucinated_old_year():
    schedule = parse_schedule_item(
        {
            "title": "期末考试",
            "date": "2023-12-30",
            "date_year_explicit": False,
        },
        today=datetime.date(2026, 7, 28),
    )
    assert schedule["date"] == datetime.date(2026, 12, 30)


def test_yearless_january_date_rolls_over_after_new_year_boundary():
    schedule = parse_schedule_item(
        {
            "title": "元旦活动",
            "date": "2026-01-01",
            "date_year_explicit": False,
        },
        today=datetime.date(2026, 12, 30),
    )
    assert schedule["date"] == datetime.date(2027, 1, 1)


def test_explicit_year_is_not_rewritten():
    schedule = parse_schedule_item(
        {
            "title": "历史记录",
            "date": "2023-12-30",
            "date_year_explicit": True,
        },
        today=datetime.date(2026, 7, 28),
    )
    assert schedule["date"] == datetime.date(2023, 12, 30)


def test_month_day_parser_handles_next_leap_year():
    assert resolve_unspecified_year_date(2, 29, datetime.date(2027, 12, 30)) == datetime.date(
        2028, 2, 29
    )


def test_model_response_accepts_the_year_explicitness_field():
    items = parse_model_response(
        '{"schedules": [{"title": "考试", "date": "2023-12-30", '
        '"date_year_explicit": false}]}'
    )
    assert items[0]["date_year_explicit"] is False


def test_strict_time_parser_rejects_invalid_clock_values():
    schedule = parse_schedule_item(
        {
            "title": "测试",
            "date": "2026-07-28",
            "date_year_explicit": True,
            "start_time": "25:70",
            "end_time": "09:30 extra",
        },
        today=datetime.date(2026, 7, 28),
    )

    assert schedule["start_time"] is None
    assert schedule["end_time"] is None
