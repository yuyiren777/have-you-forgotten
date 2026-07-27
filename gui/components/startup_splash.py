"""Lightweight animated splash screen shown while the application starts."""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget


class StartupSplash(QWidget):
    """A small, local-only startup buffer for the desktop application."""

    TITLE = 'AI备忘录启动中...'

    def __init__(self):
        super().__init__()
        self._phase = 0
        self.setFixedSize(720, 420)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._advance_animation)
        self._animation_timer.start(85)

    def _advance_animation(self):
        self._phase = (self._phase + 18) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#17323A'))

        painter.setPen(QPen(QColor('#41636A'), 1))
        painter.drawRect(20, 20, self.width() - 41, self.height() - 41)
        painter.drawLine(54, 104, self.width() - 54, 104)
        painter.drawLine(54, 318, self.width() - 54, 318)

        painter.setPen(QColor('#83BDB4'))
        mark_font = QFont('Segoe UI', 76)
        mark_font.setBold(True)
        painter.setFont(mark_font)
        painter.drawText(58, 208, 'AI')

        painter.setPen(QColor('#A8C6C8'))
        label_font = QFont('Microsoft YaHei UI', 10)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(label_font)
        painter.drawText(216, 140, 'PERSONAL MEMORY ASSISTANT')

        title_font = QFont('Microsoft YaHei UI', 31)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor('#0A171B'))
        painter.drawText(216, 187, self.TITLE)
        painter.setPen(QColor('#F2C66D'))
        painter.drawText(212, 183, self.TITLE)

        painter.setPen(QColor('#A8C6C8'))
        detail_font = QFont('Microsoft YaHei UI', 12)
        painter.setFont(detail_font)
        painter.drawText(216, 229, '正在整理你的待办与提醒')

        spinner_pen = QPen(QColor('#F2C66D'), 4)
        spinner_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(spinner_pen)
        painter.drawArc(57, 345, 30, 30, -self._phase * 16, 235 * 16)

        painter.setPen(QColor('#A8C6C8'))
        status_font = QFont('Microsoft YaHei UI', 11)
        painter.setFont(status_font)
        painter.drawText(104, 367, '正在加载本地服务')
