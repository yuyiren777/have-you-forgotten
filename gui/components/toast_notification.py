"""Toast 通知组件 — 右下角弹窗"""
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont


class ToastNotification(QDialog):
    """右下角弹出通知"""

    dismissed = pyqtSignal()
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
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            #ToastNotification {
                background: #FFFFFF;
                border: 1px solid #C9D2D8;
                border-radius: 8px;
            }
            #ToastContent, #ToastScroll { background: #FFFFFF; border: none; }
            #ToastTitle { color: #17242D; }
            #ToastMessage { color: #26343F; font-size: 11pt; }
            #ToastScroll QScrollBar:vertical {
                background: #EEF2F3; width: 10px; margin: 0;
            }
            #ToastScroll QScrollBar::handle:vertical {
                background: #6B7E86; min-height: 28px; border-radius: 4px;
            }
            #ToastScroll QScrollBar::add-line:vertical,
            #ToastScroll QScrollBar::sub-line:vertical { height: 0; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)
        dialog_width = min(520, max(380, int(available.width() * 0.38)))
        maximum_height = min(520, max(260, int(available.height() * 0.68)))

        self.content_scroll = QScrollArea()
        self.content_scroll.setObjectName('ToastScroll')
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName('ToastContent')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(10)

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setObjectName('ToastTitle')
        self.title_label.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        content_layout.addWidget(self.title_label)

        # 内容
        self.message_label = QLabel(message)
        self.message_label.setObjectName('ToastMessage')
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.message_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        content_layout.addWidget(self.message_label)
        self.content_scroll.setWidget(content)
        layout.addWidget(self.content_scroll, 1)

        text_width = dialog_width - 58
        wrap_flags = Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextExpandTabs
        title_height = self.title_label.fontMetrics().boundingRect(
            QRect(0, 0, text_width, 10000), int(wrap_flags), title
        ).height()
        message_height = self.message_label.fontMetrics().boundingRect(
            QRect(0, 0, text_width, 10000), int(wrap_flags), message
        ).height()
        content_height = max(68, title_height + message_height + 18)
        content.setMinimumHeight(content_height)
        scroll_height = min(content_height + 4, maximum_height - 78)
        self.resize(dialog_width, min(maximum_height, scroll_height + 78))

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.dismiss_btn = QPushButton('知道了')
        self.dismiss_btn.setObjectName('PrimarySmallButton')
        self.dismiss_btn.clicked.connect(self._on_dismiss)
        btn_layout.addWidget(self.dismiss_btn)
        layout.addLayout(btn_layout)

    def _on_dismiss(self):
        self._auto_close_timer.stop()
        self.dismissed.emit()
        self.close()

    def _fade_out(self):
        self.close()

    def closeEvent(self, event):
        """Release the strong reference after the native window closes."""
        self._active_toasts.discard(self)
        super().closeEvent(event)

    @staticmethod
    def show_notification(title: str, message: str, parent=None, modal: bool = False):
        """在屏幕右下角显示通知"""
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

        if modal:
            # Reminder dialogs must remain available until the user acknowledges them.
            toast._auto_close_timer.stop()
            toast.setWindowModality(Qt.WindowModality.ApplicationModal)
            toast.exec_()
        else:
            toast.show()
            toast.raise_()
            toast.activateWindow()
        return toast
