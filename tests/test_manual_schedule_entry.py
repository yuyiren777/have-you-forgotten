import os
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QScrollArea

from gui.home_page import HomePage


def _page():
    app = QApplication.instance() or QApplication([])
    with patch("gui.home_page.get_model_name", return_value="测试模型"):
        page = HomePage()
    return app, page


def test_manual_entry_is_available_below_a_visible_scrollbar():
    app, page = _page()
    left_scroll = page.findChild(QScrollArea, "LeftScroll")

    assert left_scroll is not None
    assert left_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOn
    assert page.manual_add_btn.text() == "手动填写日程"
    assert page.manual_add_btn.isEnabled()

    page.deleteLater()
    app.processEvents()


def test_manual_entry_refreshes_overview_only_after_saving():
    app, page = _page()
    page.refresh_schedules = Mock()

    with patch("gui.home_page.open_schedule_creator", side_effect=[False, True]) as creator:
        page._on_manual_add()
        page._on_manual_add()

    assert creator.call_count == 2
    page.refresh_schedules.assert_called_once_with()

    page.deleteLater()
    app.processEvents()
