import datetime
from types import SimpleNamespace

from core.reminder import _is_schedule_expired


def _schedule(date, start_time=None, end_time=None):
    return SimpleNamespace(
        date=date,
        start_time=start_time,
        end_time=end_time,
    )


def test_undated_schedule_is_never_auto_expired():
    assert not _is_schedule_expired(_schedule(None), datetime.datetime(2026, 8, 6, 23, 0))


def test_date_only_schedule_expires_at_10pm_not_midnight():
    schedule = _schedule(datetime.date(2026, 8, 6))

    assert not _is_schedule_expired(schedule, datetime.datetime(2026, 8, 6, 21, 59))
    assert _is_schedule_expired(schedule, datetime.datetime(2026, 8, 6, 22, 0))


def test_timed_schedule_without_end_expires_after_one_hour_grace():
    schedule = _schedule(datetime.date(2026, 8, 6), datetime.time(15, 0))

    assert not _is_schedule_expired(schedule, datetime.datetime(2026, 8, 6, 15, 59))
    assert _is_schedule_expired(schedule, datetime.datetime(2026, 8, 6, 16, 0))


def test_overnight_schedule_expires_on_following_day_after_end_time():
    schedule = _schedule(
        datetime.date(2026, 8, 6),
        datetime.time(23, 30),
        datetime.time(1, 0),
    )

    assert not _is_schedule_expired(schedule, datetime.datetime(2026, 8, 7, 0, 59))
    assert _is_schedule_expired(schedule, datetime.datetime(2026, 8, 7, 1, 0))
