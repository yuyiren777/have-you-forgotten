import datetime
import os
from types import SimpleNamespace

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
