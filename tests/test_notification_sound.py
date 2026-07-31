import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMainWindow

from gui.main_window import MainWindow
from utils.notification_sound import play_reminder_sound


def test_windows_system_sound_is_preferred():
    message_beep = Mock(return_value=True)
    fake_winsound = SimpleNamespace(
        MB_ICONEXCLAMATION=48,
        MessageBeep=message_beep,
    )

    with patch.dict(sys.modules, {"winsound": fake_winsound}):
        assert play_reminder_sound()

    message_beep.assert_called_once_with(48)


def test_reminder_popup_plays_sound_before_showing_modal_dialog():
    app = QApplication.instance() or QApplication([])
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    calls = []

    with patch("gui.main_window.play_reminder_sound", side_effect=lambda: calls.append("sound")), patch(
        "gui.main_window.ToastNotification.show_notification",
        side_effect=lambda *args, **kwargs: calls.append("popup"),
    ) as show_notification:
        window._show_reminder_toast("最后提醒", "提交材料")

    assert calls == ["sound", "popup"]
    show_notification.assert_called_once_with(
        "最后提醒", "提交材料", window, modal=True
    )
    window.deleteLater()
    app.processEvents()
