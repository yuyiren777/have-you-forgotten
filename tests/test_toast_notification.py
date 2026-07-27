import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from gui.components.toast_notification import ToastNotification


def test_visible_toast_is_retained_and_released_when_closed():
    app = QApplication.instance() or QApplication([])
    toast = ToastNotification.show_notification("Title", "Message")

    assert toast in ToastNotification._active_toasts

    toast.close()
    app.processEvents()
    assert toast not in ToastNotification._active_toasts
