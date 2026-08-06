import datetime
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget

from gui.components.modern_checkbox import ModernCheckBox
from gui.components.schedule_card import ScheduleCard
from gui.reminder_history import ReminderHistoryPage


def _schedule(status="reminded"):
    return SimpleNamespace(
        id=17,
        title="测试提醒",
        urgency=1,
        status=status,
        date=datetime.date(2026, 8, 1),
        start_time=datetime.time(9, 0),
        end_time=None,
        location=None,
        notes=None,
    )


class _FakeQuery:
    def __init__(self, schedules):
        self.schedules = schedules

    def where(self, *args):
        return self

    def order_by(self, *args):
        return self

    def __iter__(self):
        return iter(self.schedules)


def test_modern_checkbox_is_large_and_clickable():
    app = QApplication.instance() or QApplication([])
    checkbox = ModernCheckBox("开机后后台启动")
    checkbox.resize(260, 42)
    checkbox.show()

    QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=checkbox.rect().center())

    assert checkbox.isChecked()
    assert checkbox.sizeHint().height() >= 32
    assert checkbox.INDICATOR_SIZE >= 22
    checkbox.deleteLater()
    app.processEvents()


def test_modern_checkbox_entire_visible_area_toggles_reliably():
    app = QApplication.instance() or QApplication([])
    checkbox = ModernCheckBox("开机后后台启动（可在系统托盘中打开）")
    checkbox.resize(420, 44)
    checkbox.show()
    app.processEvents()

    positions = (
        QPoint(1, 1),
        QPoint(21, checkbox.height() // 2),
        QPoint(180, checkbox.height() // 2),
        QPoint(checkbox.width() - 2, checkbox.height() - 2),
    )
    expected = False
    for _ in range(5):
        for position in positions:
            QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=position)
            expected = not expected
            assert checkbox.isChecked() is expected

    assert checkbox.hitButton(QPoint(0, 0))
    assert not checkbox.hitButton(QPoint(-1, -1))
    checkbox.deleteLater()
    app.processEvents()


def test_icon_only_checkbox_keeps_full_indicator_hit_area():
    app = QApplication.instance() or QApplication([])
    checkbox = ModernCheckBox()
    checkbox.resize(checkbox.sizeHint())
    checkbox.show()
    app.processEvents()

    QTest.mouseClick(
        checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(checkbox.width() - 1, checkbox.height() - 1),
    )

    assert checkbox.isChecked()
    assert checkbox.width() >= checkbox.INDICATOR_SIZE + 6
    checkbox.deleteLater()
    app.processEvents()


def test_modern_checkbox_detects_parent_dark_theme_stylesheet():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.setStyleSheet("/* night theme */ QWidget { background: #171D1F; }")
    checkbox = ModernCheckBox(parent=parent)

    assert checkbox._uses_dark_theme()
    parent.deleteLater()
    app.processEvents()


def test_reminder_history_cards_expose_delete_button_for_every_status():
    app = QApplication.instance() or QApplication([])
    page = ReminderHistoryPage()

    for status, layout in (
        ("reminded", page.reminded_layout),
        ("expired", page.expired_layout),
        ("completed", page.completed_layout),
    ):
        schedule = _schedule(status)
        with patch("gui.reminder_history.Schedule.select", return_value=_FakeQuery([schedule])):
            page._refresh_tab(status, layout)
        card = next(card for card in page.findChildren(ScheduleCard) if card.schedule is schedule)
        assert any(
            button.text() == "删除" and button.objectName() == "DangerButton"
            for button in card.findChildren(QPushButton)
        )

    page.deleteLater()
    app.processEvents()


def test_reminder_history_refreshes_statuses_before_rendering_tabs():
    app = QApplication.instance() or QApplication([])
    page = ReminderHistoryPage()
    empty_query = _FakeQuery([])

    with patch("gui.reminder_history.refresh_expired_schedule_statuses") as sync, patch(
        "gui.reminder_history.Schedule.select", return_value=empty_query
    ):
        page.refresh()

    sync.assert_called_once_with()
    page.deleteLater()
    app.processEvents()


def test_reminder_history_timer_only_refreshes_while_visible():
    app = QApplication.instance() or QApplication([])
    page = ReminderHistoryPage()

    with patch.object(page, "isVisible", return_value=False), patch.object(page, "refresh") as refresh:
        page._refresh_if_visible()
        refresh.assert_not_called()

    with patch.object(page, "isVisible", return_value=True), patch.object(page, "refresh") as refresh:
        page._refresh_if_visible()
        refresh.assert_called_once_with()

    assert page._refresh_timer.interval() == 30_000
    page.deleteLater()
    app.processEvents()


def test_theme_scrollbars_have_visible_tracks_and_handles():
    project_root = os.path.dirname(os.path.dirname(__file__))
    for filename in ("styles.qss", "dark_styles.qss"):
        with open(os.path.join(project_root, "gui", filename), encoding="utf-8") as stream:
            stylesheet = stream.read()

        assert stylesheet.count("QScrollBar:vertical {") == 1
        assert "width: 16px;" in stylesheet
        assert "min-height: 54px;" in stylesheet
        assert "QScrollBar:horizontal" in stylesheet
        assert "min-width: 54px;" in stylesheet
