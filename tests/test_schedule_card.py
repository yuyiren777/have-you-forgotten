import datetime
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QPushButton

from gui.components.schedule_card import ScheduleCard
from gui.components.modern_checkbox import ModernCheckBox


def _schedule():
    return SimpleNamespace(
        id=7,
        title="写数学",
        urgency=0,
        status="pending",
        date=datetime.date(2026, 7, 29),
        start_time=datetime.time(15, 0),
        end_time=datetime.time(17, 0),
        location=None,
        notes=None,
    )


def test_overview_card_exposes_delete_button_and_emits_schedule_id():
    app = QApplication.instance() or QApplication([])
    card = ScheduleCard(_schedule(), show_delete_button=True)
    emitted = []
    card.deleted.connect(emitted.append)
    delete_button = next(
        button for button in card.findChildren(QPushButton) if button.text() == "删除"
    )

    delete_button.click()

    assert delete_button.objectName() == "DangerButton"
    assert emitted == [7]
    card.deleteLater()
    app.processEvents()


def test_shared_card_does_not_show_delete_button_unless_requested():
    app = QApplication.instance() or QApplication([])
    card = ScheduleCard(_schedule())

    assert not any(
        button.text() == "删除" for button in card.findChildren(QPushButton)
    )
    card.deleteLater()
    app.processEvents()


def test_schedule_selection_uses_high_visibility_checkbox():
    app = QApplication.instance() or QApplication([])
    card = ScheduleCard(_schedule())

    assert isinstance(card.select_box, ModernCheckBox)
    assert card.select_box.INDICATOR_SIZE >= 22
    card.deleteLater()
    app.processEvents()


def test_schedule_card_exposes_edit_button_and_emits_schedule_id():
    app = QApplication.instance() or QApplication([])
    card = ScheduleCard(_schedule())
    emitted = []
    card.edit_requested.connect(emitted.append)
    edit_button = next(
        button for button in card.findChildren(QPushButton) if button.text() == "编辑"
    )

    edit_button.click()

    assert edit_button.toolTip() == "编辑日程内容、时间、紧急度和备注"
    assert emitted == [7]
    card.deleteLater()
    app.processEvents()


def test_pending_card_refreshes_remaining_time_without_rebuilding():
    app = QApplication.instance() or QApplication([])
    with patch(
        "gui.components.schedule_card.format_remaining_time",
        side_effect=["还有2小时", "还有1小时"],
    ):
        card = ScheduleCard(_schedule())
        original_label = card.remaining_label

        assert original_label.text() == "还有2小时"
        assert card._remaining_timer.isActive()
        assert card._remaining_timer.interval() == card.RELATIVE_TIME_REFRESH_MS

        card._remaining_timer.timeout.emit()

    assert card.remaining_label is original_label
    assert card.remaining_label.text() == "还有1小时"
    card.deleteLater()
    app.processEvents()


def test_completed_card_does_not_start_relative_time_timer():
    app = QApplication.instance() or QApplication([])
    schedule = _schedule()
    schedule.status = "completed"

    card = ScheduleCard(schedule)

    assert card.remaining_label is None
    assert card._remaining_timer is None
    card.deleteLater()
    app.processEvents()
