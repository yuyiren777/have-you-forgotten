"""骨架屏加载动画 — 识别过程中的加载效果"""
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, Qt
from PyQt5.QtGui import QColor, QPalette


class ShimmerLoader(QFrame):
    """Shimmer 加载动画"""

    def __init__(self, text: str = '正在识别中...', parent=None):
        super().__init__(parent)
        self.setObjectName('ShimmerLoader')
        self._opacity = 0.3
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel('🔍')
        self.icon_label.setStyleSheet('font-size: 26pt;')
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel(text)
        self.text_label.setStyleSheet('font-size: 12pt; color: #56636D;')
        layout.addWidget(self.text_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.progress_label = QLabel('')
        self.progress_label.setStyleSheet('font-size: 11pt; color: #6F7D87;')
        layout.addWidget(self.progress_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setMinimumHeight(120)
        self.setStyleSheet("""
            #ShimmerLoader {
                background: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        # 呼吸动画
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(800)
        self._growing = True

    def _animate(self):
        if self._growing:
            self._opacity = min(1.0, self._opacity + 0.1)
            if self._opacity >= 1.0:
                self._growing = False
        else:
            self._opacity = max(0.3, self._opacity - 0.1)
            if self._opacity <= 0.3:
                self._growing = True

        color = QColor(100, 100, 100, int(self._opacity * 200))
        self.text_label.setStyleSheet(f'font-size: 12pt; color: {color.name()};')

    def set_progress(self, text: str):
        self.progress_label.setText(text)

    def set_text(self, text: str):
        self.text_label.setText(text)

    def stop(self):
        self._timer.stop()
