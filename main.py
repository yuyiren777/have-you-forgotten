"""智能日程提醒助手 — 应用入口"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMessageBox

from db.database import init_db
from gui.components.startup_splash import StartupSplash
from utils.single_instance import SingleInstanceGuard


class StartupWorker(QThread):
    """Load non-widget startup dependencies without blocking the splash UI."""

    ready = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.window_type = None

    def run(self):
        try:
            from core.frameworks import verify_ai_frameworks
            from gui.main_window import MainWindow

            verify_ai_frameworks()
            init_db()
            self.window_type = MainWindow
            self.ready.emit()
        except Exception as error:
            self.failed.emit(str(error))


def main():
    if '--verify-runtime' in sys.argv:
        import tempfile
        from pathlib import Path

        from openpyxl import load_workbook

        from core.exporter import export_schedules
        from core.frameworks import verify_ai_frameworks
        from core.workflow import schedule_workflow

        verify_ai_frameworks()
        if schedule_workflow is None:
            raise RuntimeError('LangGraph workflow compilation failed.')
        with tempfile.TemporaryDirectory() as temporary_directory:
            export_path = Path(temporary_directory) / 'runtime-check.xlsx'
            export_schedules([], str(export_path), 'xlsx')
            workbook = load_workbook(export_path, read_only=True)
            workbook.close()
        return

    # 初始化数据库

    # Follow the Windows display scale instead of rendering CSS pixels too small.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setFont(QFont('Microsoft YaHei UI', 13))
    app.setApplicationName('智能日程提醒助手')
    app.setOrganizationName('ScheduleAssistant')
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，后台运行
    background_start = '--background' in sys.argv
    instance_guard = SingleInstanceGuard(app)
    if not instance_guard.is_primary:
        return
    app.instance_guard = instance_guard
    app.activation_pending = False

    def activate_main_window():
        window = getattr(app, 'main_window', None)
        if window:
            window.show_and_raise()
        else:
            app.activation_pending = True

    instance_guard.activation_requested.connect(activate_main_window)
    app.aboutToQuit.connect(instance_guard.close)

    # A startup launch keeps only the tray and reminder service visible.
    splash = None
    if not background_start:
        splash = StartupSplash()
        splash.show()
        app.processEvents()

    startup_worker = StartupWorker()

    def show_main_window():
        try:
            window = startup_worker.window_type(show_developer_note=not background_start)
            app.main_window = window
            if background_start and not app.activation_pending:
                window.tray.show()
            else:
                window.show_and_raise()
            if splash:
                splash.close()
        except Exception as error:
            if splash:
                splash.close()
            QMessageBox.critical(None, '启动失败', f'无法打开应用：{error}')
            app.quit()

    def show_startup_error(message: str):
        if splash:
            splash.close()
        QMessageBox.critical(None, '启动失败', f'初始化本地服务失败：{message}')
        app.quit()

    startup_worker.ready.connect(show_main_window)
    startup_worker.failed.connect(show_startup_error)
    startup_worker.start()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
