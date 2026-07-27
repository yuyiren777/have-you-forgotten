"""Toast 通知组件 — 右下角弹窗"""
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont


class ToastNotification(QFrame):
    """右下角弹出通知"""

    dismissed = pyqtSignal()
    snoozed = pyqtSignal()  # 稍后提醒
    _active_toasts = set()

    def __init__(self, title: str = '', message: str = '', parent=None):
        super().__init__(parent)
        self.setObjectName('ToastNotification')
        self._setup_ui(title, message)
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.timeout.connect(self._fade_out)
        self._auto_close_timer.start(10000)  # 10秒自动消失

    def _setup_ui(self, title: str, message: str):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(320, 140)
        self.setStyleSheet("""
            #ToastNotification {
                background: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 内容
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet('color: #555; font-size: 11pt;')
        layout.addWidget(msg_label)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        snooze_btn = QPushButton('10分钟后')
        snooze_btn.setObjectName('SmallButton')
        snooze_btn.clicked.connect(self._on_snooze)
        btn_layout.addWidget(snooze_btn)

        dismiss_btn = QPushButton('知道了')
        dismiss_btn.setObjectName('PrimarySmallButton')
        dismiss_btn.clicked.connect(self._on_dismiss)
        btn_layout.addWidget(dismiss_btn)
        layout.addLayout(btn_layout)

    def _on_dismiss(self):
        self._auto_close_timer.stop()
        self.dismissed.emit()
        self.close()

    def _on_snooze(self):
        self._auto_close_timer.stop()
        self.snoozed.emit()
        self.close()

    def _fade_out(self):
        self.close()

    def closeEvent(self, event):
        """Release the strong reference after the native window closes."""
        self._active_toasts.discard(self)
        super().closeEvent(event)

    @staticmethod
    def show_notification(title: str, message: str, parent=None):
        """在屏幕右下角显示通知"""
        from PyQt5.QtWidgets import QApplication
        toast = ToastNotification(title, message, parent)
        # Callers generally do not keep the returned widget. Retain it while
        # visible so Python cannot destroy its native window prematurely.
        ToastNotification._active_toasts.add(toast)

        # 定位到右下角
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = screen_geo.right() - toast.width() - 20
            y = screen_geo.bottom() - toast.height() - 20
            toast.move(x, y)

        toast.show()
        return toast
