import os
import tempfile
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QColor, QKeyEvent, QPixmap
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget

from gui.components.image_drop_zone import ImageDropZone
from gui.main_window import MainWindow


def test_image_drop_zone_accepts_clipboard_bitmap_and_saves_it_once():
    app = QApplication.instance() or QApplication([])
    clipboard = app.clipboard()
    pixmap = QPixmap(24, 18)
    pixmap.fill(QColor("#2B7A78"))
    clipboard.setPixmap(pixmap)

    with tempfile.TemporaryDirectory() as data_dir, patch(
        "gui.components.image_drop_zone.DATA_DIR", data_dir
    ):
        zone = ImageDropZone()
        added = zone.paste_from_clipboard(clipboard)

        assert len(added) == 1
        assert zone.get_images() == added
        assert os.path.isfile(added[0])
        assert os.path.getsize(added[0]) > 0
        zone.deleteLater()
    clipboard.clear()
    app.processEvents()


def test_image_drop_zone_is_keyboard_focusable():
    app = QApplication.instance() or QApplication([])
    zone = ImageDropZone()

    assert zone.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert "Ctrl+V" in zone.toolTip()
    assert "Ctrl+V" in zone.hint_label.text()
    zone.show()
    zone.activateWindow()
    QTest.mouseClick(zone, Qt.MouseButton.LeftButton, pos=zone.rect().center())
    app.processEvents()
    assert zone.hasFocus()
    zone.deleteLater()
    app.processEvents()


def test_main_window_intercepts_image_paste_before_text_widget():
    app = QApplication.instance() or QApplication([])
    clipboard = app.clipboard()
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor("#FF9800"))
    clipboard.setPixmap(pixmap)

    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    page = QWidget()
    page.drop_zone = ImageDropZone(page)
    window.home_page = page
    window.stack = QStackedWidget(window)
    window.stack.addWidget(page)
    window.stack.setCurrentWidget(page)
    window._clipboard_paste_token = 0
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_V,
        Qt.KeyboardModifier.ControlModifier,
    )

    with patch.object(window, "isActiveWindow", return_value=True), patch.object(
        window, "_request_clipboard_image_paste"
    ) as request_paste:
        consumed = window.eventFilter(page.drop_zone, event)

    assert consumed is True
    request_paste.assert_called_once_with(show_empty=False)
    window.deleteLater()
    clipboard.clear()
    app.processEvents()


def test_delayed_screenshot_clipboard_is_retried_without_blocking():
    app = QApplication.instance() or QApplication([])
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    page = QWidget()
    page.drop_zone = ImageDropZone(page)
    window.home_page = page
    window.stack = QStackedWidget(window)
    window.stack.addWidget(page)
    window._clipboard_paste_token = 0

    with patch.object(
        page.drop_zone,
        "paste_from_clipboard",
        side_effect=[[], ["delayed-screenshot.png"]],
    ) as paste, patch(
        "gui.main_window.QTimer.singleShot",
        side_effect=lambda delay, callback: callback(),
    ) as single_shot, patch.object(window, "_switch_page"), patch(
        "gui.main_window.ToastNotification.show_notification"
    ):
        window._request_clipboard_image_paste()

    assert paste.call_count == 2
    assert single_shot.call_count == 1
    assert single_shot.call_args.args[0] == 80
    window.deleteLater()
    app.processEvents()
