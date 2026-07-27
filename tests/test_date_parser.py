from utils.date_parser import format_remaining_time


def test_remaining_time_handles_missing_date():
    assert format_remaining_time(None) == '未设日期'
