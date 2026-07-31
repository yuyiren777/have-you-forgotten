import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QApplication

from utils.system_tray import SystemTray


def test_tray_keeps_context_menu_and_exit_action_alive():
    app = QApplication.instance() or QApplication([])
    tray = SystemTray()
    exit_spy = QSignalSpy(tray.quit_app)

    assert tray._tray.contextMenu() is tray._menu
    assert tray._quit_action in tray._menu.actions()
    assert tray._quit_action.text() == "退出应用"

    tray._quit_action.trigger()
    app.processEvents()

    assert len(exit_spy) == 1
    tray.shutdown()
    tray.deleteLater()
    app.processEvents()
