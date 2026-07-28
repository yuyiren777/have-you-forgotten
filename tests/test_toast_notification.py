import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest

from gui.components.toast_notification import ToastNotification


def test_visible_toast_is_retained_and_released_when_closed():
    app = QApplication.instance() or QApplication([])
    toast = ToastNotification.show_notification("Title", "Message")

    assert toast in ToastNotification._active_toasts

    toast.close()
    app.processEvents()
    assert toast not in ToastNotification._active_toasts


def test_toast_has_only_a_dismiss_action():
    app = QApplication.instance() or QApplication([])
    toast = ToastNotification.show_notification("Title", "Message")

    assert toast.dismiss_btn.text() == "知道了"
    assert not hasattr(toast, "snooze_btn")
    toast.close()
    app.processEvents()


def test_dismiss_action_closes_the_dialog_after_a_mouse_click():
    app = QApplication.instance() or QApplication([])
    toast = ToastNotification.show_notification("Title", "Message")

    QTest.mouseClick(toast.dismiss_btn, Qt.MouseButton.LeftButton)
    app.processEvents()

    assert toast not in ToastNotification._active_toasts


def test_modal_toast_can_be_dismissed_from_its_button():
    app = QApplication.instance() or QApplication([])
    toast = ToastNotification("Title", "Message")
    ToastNotification._active_toasts.add(toast)
    toast.setWindowModality(Qt.WindowModality.ApplicationModal)

    QTimer.singleShot(
        0, lambda: QTest.mouseClick(toast.dismiss_btn, Qt.MouseButton.LeftButton)
    )
    toast.exec_()
    app.processEvents()

    assert toast not in ToastNotification._active_toasts
