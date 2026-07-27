"""智能日程提醒助手 — 应用入口"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from db.database import init_db
from gui.main_window import MainWindow


def main():
    # 初始化数据库
    init_db()

    # Follow the Windows display scale instead of rendering CSS pixels too small.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setFont(QFont('Microsoft YaHei UI', 13))
    app.setApplicationName('智能日程提醒助手')
    app.setOrganizationName('ScheduleAssistant')
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，后台运行

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
