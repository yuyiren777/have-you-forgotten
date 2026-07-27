import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtWidgets import QApplication

from gui.components.startup_splash import StartupSplash


def test_startup_splash_has_expected_title_and_dimensions():
    QApplication.instance() or QApplication([])
    splash = StartupSplash()

    assert splash.TITLE == 'AI备忘录启动中...'
    assert splash.size().width() == 720
    assert splash.size().height() == 420
    splash.close()
