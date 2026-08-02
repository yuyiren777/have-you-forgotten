import datetime

from core.reminder import (
    _schedule_reminder_window,
    _select_due_stage,
    _skipped_stage_keys,
)


def test_nearest_due_stage_is_selected_without_replaying_missed_stages():
    stages = [
        ("first", "第一次提醒", 300 * 24 * 60),
        ("second", "第二次提醒", 7 * 24 * 60),
        ("final", "最后提醒", 30),
    ]

    selected = _select_due_stage(6 * 24 * 60, stages, set())

    assert selected[0] == "second"


def test_final_stage_is_selected_for_events_only_minutes_away():
    stages = [
        ("first", "第一次提醒", 7 * 24 * 60),
        ("second", "第二次提醒", 3 * 24 * 60),
        ("final", "最后提醒", 30),
    ]

    selected = _select_due_stage(10, stages, {"first", "second"})

    assert selected[0] == "final"


def test_missed_early_stage_is_marked_skipped_instead_of_replayed_later():
    stages = [
        ("first", "第一次提醒", 7 * 24 * 60),
        ("second", "第二次提醒", 24 * 60),
        ("final", "最后提醒", 30),
    ]
    selected = _select_due_stage(12 * 60, stages, set())

    assert selected[0] == "second"
    assert _skipped_stage_keys(selected, stages, set()) == ["first"]


def test_event_just_started_can_receive_the_final_catch_up_reminder():
    stages = [
        ("first", "第一次提醒", 24 * 60),
        ("final", "最后提醒", 30),
    ]

    assert _select_due_stage(-5, stages, set())[0] == "final"


def test_all_day_schedule_remains_remindable_until_10pm():
    target, deadline = _schedule_reminder_window(
        datetime.date(2026, 7, 28), None, None
    )

    assert target == datetime.datetime(2026, 7, 28, 12, 0)
    assert deadline == datetime.datetime(2026, 7, 28, 22, 0)


def test_overnight_schedule_deadline_is_on_the_next_day():
    target, deadline = _schedule_reminder_window(
        datetime.date(2026, 7, 28), datetime.time(23, 30), datetime.time(1, 0)
    )

    assert target == datetime.datetime(2026, 7, 28, 23, 30)
    assert deadline == datetime.datetime(2026, 7, 29, 1, 0)


def test_equal_start_and_end_is_not_treated_as_a_24_hour_event():
    target, deadline = _schedule_reminder_window(
        datetime.date(2026, 7, 28), datetime.time(9, 0), datetime.time(9, 0)
    )

    assert deadline == target + datetime.timedelta(hours=1)
