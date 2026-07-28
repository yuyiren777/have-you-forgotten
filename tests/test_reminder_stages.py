from core.reminder import _select_due_stage


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
