import datetime
import os
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QDate, Qt, QTime
from PyQt5.QtWidgets import QApplication

from gui.components.schedule_edit_dialog import (
    ScheduleEditDialog,
    apply_schedule_edits,
    create_schedule_from_changes,
)


def _schedule(**overrides):
    values = {
        "id": 9,
        "title": "高数考试",
        "location": "A101",
        "date": datetime.date(2026, 8, 10),
        "start_time": datetime.time(9, 0),
        "end_time": datetime.time(11, 0),
        "status": "pending",
        "reminded_at": None,
        "updated_at": datetime.datetime(2026, 7, 31, 9, 0),
        "save": Mock(),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_editor_loads_and_returns_corrected_time_and_location():
    app = QApplication.instance() or QApplication([])
    dialog = ScheduleEditDialog(_schedule())
    dialog.location_input.setText("明辨楼 C555")
    dialog.date_edit.setDate(QDate(2026, 12, 30))
    dialog.start_time_edit.setTime(QTime(14, 30))
    dialog.end_time_edit.setTime(QTime(16, 0))

    changes = dialog.changes()

    assert changes["location"] == "明辨楼 C555"
    assert changes["date"] == datetime.date(2026, 12, 30)
    assert changes["start_time"] == datetime.time(14, 30)
    assert changes["end_time"] == datetime.time(16, 0)
    dialog.deleteLater()
    app.processEvents()


def test_editor_does_not_show_nonfunctional_context_help_button():
    app = QApplication.instance() or QApplication([])
    dialog = ScheduleEditDialog(_schedule())

    assert not dialog.windowFlags() & Qt.WindowType.WindowContextHelpButtonHint

    dialog.deleteLater()
    app.processEvents()


def test_manual_creator_uses_blank_fields_and_optional_time():
    app = QApplication.instance() or QApplication([])
    dialog = ScheduleEditDialog()

    assert dialog.is_new
    assert dialog.windowTitle() == "手动添加日程"
    assert dialog.title_input.text() == ""
    assert dialog.date_check.isChecked()
    assert not dialog.start_check.isChecked()
    assert not dialog.end_check.isEnabled()

    dialog.deleteLater()
    app.processEvents()


def test_manual_schedule_is_saved_with_normalized_fields():
    changes = {
        "title": "线下开会",
        "location": "A101",
        "date": datetime.date(2026, 8, 2),
        "start_time": datetime.time(10, 0),
        "end_time": None,
    }
    created = Mock()

    with patch("gui.components.schedule_edit_dialog.db.atomic", return_value=nullcontext()), patch(
        "gui.components.schedule_edit_dialog.Schedule.create",
        return_value=created,
    ) as create:
        result = create_schedule_from_changes(changes)

    assert result is created
    create.assert_called_once_with(**changes)


def test_unchecking_date_clears_date_and_both_times():
    app = QApplication.instance() or QApplication([])
    dialog = ScheduleEditDialog(_schedule())

    dialog.date_check.setChecked(False)
    changes = dialog.changes()

    assert changes["date"] is None
    assert changes["start_time"] is None
    assert changes["end_time"] is None
    assert not dialog.start_check.isEnabled()
    assert not dialog.end_check.isEnabled()
    dialog.deleteLater()
    app.processEvents()


def test_timing_correction_resets_old_reminder_state_and_logs():
    schedule = _schedule(
        status="reminded",
        reminded_at=datetime.datetime(2026, 8, 10, 8, 30),
    )
    changes = {
        "title": schedule.title,
        "location": "B202",
        "date": datetime.date(2026, 8, 11),
        "start_time": datetime.time(10, 0),
        "end_time": datetime.time(12, 0),
    }
    delete_query = Mock()
    delete_query.where.return_value = delete_query

    with patch("gui.components.schedule_edit_dialog.db.atomic", return_value=nullcontext()), patch(
        "gui.components.schedule_edit_dialog.ReminderLog.delete",
        return_value=delete_query,
    ) as delete_logs:
        changed = apply_schedule_edits(schedule, changes)

    assert changed
    assert schedule.status == "pending"
    assert schedule.reminded_at is None
    assert schedule.date == datetime.date(2026, 8, 11)
    delete_logs.assert_called_once()
    delete_query.execute.assert_called_once()
    schedule.save.assert_called_once()


def test_location_only_correction_keeps_existing_reminder_history():
    schedule = _schedule()
    changes = {
        "title": schedule.title,
        "location": "新地点",
        "date": schedule.date,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
    }

    with patch("gui.components.schedule_edit_dialog.db.atomic", return_value=nullcontext()), patch(
        "gui.components.schedule_edit_dialog.ReminderLog.delete"
    ) as delete_logs:
        changed = apply_schedule_edits(schedule, changes)

    assert not changed
    assert schedule.location == "新地点"
    delete_logs.assert_not_called()
    schedule.save.assert_called_once()
