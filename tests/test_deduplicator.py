import datetime
from unittest.mock import Mock, patch

from core.deduplicator import find_duplicate


@patch("core.deduplicator.Schedule")
def test_nearby_times_are_not_merged(schedule_model):
    existing = Mock(
        title="项目会议",
        date=datetime.date(2026, 7, 27),
        start_time=datetime.time(9, 0),
    )
    schedule_model.get_or_none.return_value = None

    result = find_duplicate(
        {
            "title": "项目会议",
            "date": datetime.date(2026, 7, 27),
            "start_time": datetime.time(9, 5),
        }
    )

    assert result is None


@patch("core.deduplicator.Schedule")
def test_identical_times_are_merged(schedule_model):
    existing = Mock(
        title="项目会议",
        date=datetime.date(2026, 7, 27),
        start_time=datetime.time(9, 0),
    )
    schedule_model.get_or_none.return_value = existing

    result = find_duplicate(
        {
            "title": "项目会议",
            "date": datetime.date(2026, 7, 27),
            "start_time": datetime.time(9, 0),
        }
    )

    assert result is existing
