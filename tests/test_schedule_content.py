import datetime
from types import SimpleNamespace

from core.reminder import _build_reminder_text
from core.parser import parse_schedule_item
from utils.schedule_content import clean_optional_text, readable_notes


def test_null_like_optional_text_is_not_shown_to_users():
    assert clean_optional_text(None) == ""
    assert clean_optional_text("None") == ""
    assert clean_optional_text(" null ") == ""


def test_legacy_json_notes_only_return_human_description():
    raw = '{"title":"数学","description":"记得带计算器","urgency":"normal"}'

    assert readable_notes(raw) == "记得带计算器"
    assert readable_notes('{"description":null}') == ""


def test_new_schedule_stores_readable_notes_instead_of_model_dictionary():
    parsed = parse_schedule_item({
        "title": "学数学",
        "description": "完成第二章习题",
        "date": "2026-08-03",
        "urgency": "normal",
    })

    assert parsed["notes"] == "完成第二章习题"
    assert "{" not in parsed["notes"]


def test_reminder_uses_chinese_labels_and_never_exposes_json():
    schedule = SimpleNamespace(
        title="学数学",
        date=datetime.date(2099, 8, 2),
        start_time=None,
        end_time=None,
        location="None",
        notes='{"title":"学数学","description":null,"urgency":"normal"}',
    )

    title, content, _formatted, _remaining, location, notes = _build_reminder_text(
        schedule, "第二次提醒"
    )

    assert title == "第二次提醒：学数学"
    assert "提醒阶段：第二次提醒" in content
    assert "地点：未填写" in content
    assert "备注：未填写" in content
    assert "{" not in content
    assert location == ""
    assert notes == ""
