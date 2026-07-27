"""系统托盘管理"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QObject, pyqtSignal


class SystemTray(QObject):
    """系统托盘，支持最小化到托盘、闪烁提醒"""

    show_window = pyqtSignal()
    quit_app = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(parent)
        self._tray.setToolTip('智能日程提醒助手')

        # 设置图标
        self._normal_icon = self._make_icon('⚡')
        self._alert_icon = self._make_icon('🔔')
        self._tray.setIcon(self._normal_icon)

        # 菜单
        menu = QMenu()
        show_action = QAction('显示主窗口')
        show_action.triggered.connect(self.show_window.emit)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction('退出')
        quit_action.triggered.connect(self.quit_app.emit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _make_icon(self, emoji: str) -> QIcon:
        """用 emoji 生成简单图标"""
        from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor
        from PyQt5.QtCore import Qt
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        font = QFont('Segoe UI Emoji', 20)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        return QIcon(pixmap)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window.emit()

    def show_alert(self):
        """闪烁托盘图标提醒"""
        self._tray.setIcon(self._alert_icon)
        self._tray.showMessage(
            '日程提醒',
            '您有即将到期的日程，请查看！',
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def clear_alert(self):
        """恢复正常图标"""
        self._tray.setIcon(self._normal_icon)

    def show(self):
        self._tray.show()

    def hide(self):
        self._tray.hide()
