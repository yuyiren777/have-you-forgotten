"""主窗口 — NavigationInterface + 页面路由"""
import os
from PyQt5.QtWidgets import (
    QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
    QPushButton, QStyle, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QAction, QShortcut

from gui.home_page import HomePage
from gui.schedule_list import ScheduleListPage
from gui.reminder_history import ReminderHistoryPage
from gui.settings_page import SettingsPage
from gui.components.toast_notification import ToastNotification
from utils.system_tray import SystemTray
from core.reminder import start_reminder_service, stop_reminder_service
import core.reminder as reminder_mod


class MainWindow(QMainWindow):
    """主窗口"""

    reminder_notification = pyqtSignal(str, str)
    tray_alert_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('智能日程提醒助手')
        self.setMinimumSize(640, 480)
        self.resize(1280, 800)
        self._initial_placement_done = False
        # APScheduler invokes reminder callbacks on a worker thread. Queue all
        # GUI work back to this window's thread before touching Qt widgets.
        self.reminder_notification.connect(self._show_reminder_toast, Qt.ConnectionType.QueuedConnection)
        self.tray_alert_requested.connect(self.tray_alert, Qt.ConnectionType.QueuedConnection)

        self._setup_ui()
        self._setup_tray()
        self._setup_shortcuts()
        self._setup_reminder()

        # 加载数据
        QTimer.singleShot(300, self._init_data)
        QTimer.singleShot(500, self._show_developer_note)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== 左侧导航栏 =====
        nav = QWidget()
        nav.setObjectName('NavigationBar')
        nav.setFixedWidth(216)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(14, 20, 14, 18)
        nav_layout.setSpacing(6)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        brand_row = QHBoxLayout()
        brand_mark = QLabel('H')
        brand_mark.setObjectName('BrandMark')
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(34, 34)
        brand_row.addWidget(brand_mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_name = QLabel('Have you forgotten?')
        brand_name.setObjectName('BrandName')
        brand_text.addWidget(brand_name)
        brand_subtitle = QLabel('智能日程助手')
        brand_subtitle.setObjectName('BrandSubtitle')
        brand_text.addWidget(brand_subtitle)
        brand_row.addLayout(brand_text, 1)
        nav_layout.addLayout(brand_row)
        nav_layout.addSpacing(28)

        nav_section = QLabel('工作台')
        nav_section.setObjectName('NavSection')
        nav_layout.addWidget(nav_section)

        # 导航按钮
        self.nav_buttons = []
        nav_items = [
            (QStyle.SP_DirHomeIcon, '概览', 0),
            (QStyle.SP_FileDialogDetailedView, '所有日程', 1),
            (QStyle.SP_MessageBoxInformation, '提醒记录', 2),
            (QStyle.SP_FileDialogContentsView, '设置', 3),
        ]

        for icon_type, text, idx in nav_items:
            btn = QPushButton(text)
            btn.setObjectName('NavButton')
            btn.setIcon(self.style().standardIcon(icon_type))
            btn.setToolTip(text)
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self._switch_page(i))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()

        # 版本号
        status_label = QLabel('●  提醒服务运行中')
        status_label.setObjectName('ServiceStatus')
        nav_layout.addWidget(status_label)
        version_label = QLabel('本地数据 · v1.0')
        version_label.setObjectName('VersionLabel')
        nav_layout.addWidget(version_label)
        developer_label = QLabel('哔站 UID：402333061')
        developer_label.setObjectName('DeveloperContact')
        developer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        nav_layout.addWidget(developer_label)

        main_layout.addWidget(nav)

        # ===== 右侧页面区 =====
        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.schedule_page = ScheduleListPage()
        self.reminder_page = ReminderHistoryPage()
        self.settings_page = SettingsPage()
        self.home_page.setup_required.connect(self._open_required_setup)
        self.settings_page.setup_completed.connect(self._on_setup_completed)
        self.settings_page.theme_changed.connect(self._load_stylesheet)

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.schedule_page)
        self.stack.addWidget(self.reminder_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.stack, 1)

        # 加载样式
        self._load_stylesheet(self._saved_theme())

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)

        # 更新导航高亮
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty('active', i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # 刷新对应页面
        if index == 0:
            self.home_page.refresh_schedules()
        elif index == 1:
            self.schedule_page.refresh()
        elif index == 2:
            self.reminder_page.refresh()

    def _setup_tray(self):
        self.tray = SystemTray(self)
        self.tray.show_window.connect(self.show_and_raise)
        self.tray.quit_app.connect(self._quit_app)

        reminder_mod.on_alert_tray = self._queue_tray_alert

    def _setup_shortcuts(self):
        # Ctrl+V 粘贴截图
        from PyQt5.QtGui import QClipboard
        shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        shortcut.activated.connect(self._paste_clipboard)

    def _setup_reminder(self):
        # 设置提醒回调
        reminder_mod.on_windows_notify = self._on_reminder_notify
        # 启动后台服务
        start_reminder_service()

    def _init_data(self):
        """初始化加载数据"""
        from core.api_client import is_setup_complete

        if is_setup_complete():
            self._switch_page(0)
            return
        self._switch_page(3)
        QTimer.singleShot(200, self._show_setup_required_message)

    def _show_developer_note(self):
        """Display the opt-out developer note once per application start."""
        from db.models import Config

        setting = Config.get_or_none(Config.key == 'show_developer_note')
        if setting and setting.value == '0':
            return

        dialog = QMessageBox(self)
        dialog.setWindowTitle('开发者致语')
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setText(
            '本人学生一枚，由于忙于 408 考研，有很多东西容易忘记，\n'
            '所以开发了这个软件帮我记事。\n\n'
            '如果你觉得不错，可以在哔哩哔哩联系我，哔站 UID 在左下角；\n'
            '也欢迎反馈 Bug。\n\n'
            '本服务的日程不会保存到云端服务器，以保护你的隐私和安全。\n'
            '因此不提供 24 小时在线提醒；只有在打开电脑并运行本程序时，\n'
            '提醒服务才会启动。\n\n'
            '如果应用出现死机，请按 Shift + Ctrl + Esc 打开任务管理器，\n'
            '再结束本应用进程。'
        )
        close_button = dialog.addButton('关闭', QMessageBox.ButtonRole.RejectRole)
        never_show_button = dialog.addButton('不再弹出', QMessageBox.ButtonRole.AcceptRole)
        dialog.setDefaultButton(close_button)
        dialog.exec_()

        if dialog.clickedButton() is never_show_button:
            if setting:
                setting.value = '0'
                setting.save()
            else:
                Config.create(key='show_developer_note', value='0')

    def _show_setup_required_message(self):
        QMessageBox.information(
            self,
            '先完成设置',
            '使用日程识别前，需要先配置 AI 模型。\n\n'
            '请按页面指示完成设置；微信和邮件通知可以选择不使用。',
        )

    def _open_required_setup(self):
        self._switch_page(3)
        self.settings_page._show_step(0)
        self._show_setup_required_message()

    def _on_setup_completed(self):
        self._switch_page(0)
        ToastNotification.show_notification(
            '设置完成',
            '现在可以开始识别日程。',
            self,
        )

    def _paste_clipboard(self):
        """处理粘贴截图"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPixmap
        import uuid
        from db.database import DATA_DIR

        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()

        if not pixmap.isNull():
            # 保存截图
            images_dir = os.path.join(DATA_DIR, 'images')
            os.makedirs(images_dir, exist_ok=True)
            filename = f'clipboard_{uuid.uuid4().hex[:8]}.png'
            filepath = os.path.join(images_dir, filename)
            pixmap.save(filepath, 'PNG')

            # 添加图片并跳转到首页
            self._switch_page(0)
            self.home_page.drop_zone._add_image(filepath)

            ToastNotification.show_notification(
                '截图已添加',
                f'已从剪贴板保存截图: {filename}',
                self
            )

    def _on_reminder_notify(self, title: str, message: str):
        """Reminder callback invoked by the scheduler worker thread."""
        self.reminder_notification.emit(title, message)

    def _show_reminder_toast(self, title: str, message: str):
        # A reminder needs an explicit acknowledgement. Running the same
        # right-bottom dialog modally prevents Windows from routing clicks to
        # the background main window instead of its action button.
        ToastNotification.show_notification(title, message, self, modal=True)

    def _queue_tray_alert(self):
        self.tray_alert_requested.emit()

    def tray_alert(self):
        self.tray.show_alert()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.tray.clear_alert()

    def _quit_app(self):
        stop_reminder_service()
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘（不退出）"""
        self.hide()
        event.ignore()

    def showEvent(self, event):
        """Fit and center after the native title bar has its real size."""
        super().showEvent(event)
        if not self._initial_placement_done:
            self._initial_placement_done = True
            QTimer.singleShot(0, self._fit_and_center_on_screen)

    def _fit_and_center_on_screen(self):
        screen = self.screen()
        if not screen:
            return

        available = screen.availableGeometry()
        frame_extra_width = max(0, self.frameGeometry().width() - self.width())
        frame_extra_height = max(0, self.frameGeometry().height() - self.height())
        safe_margin = 16

        max_client_width = max(
            480, available.width() - frame_extra_width - safe_margin * 2
        )
        max_client_height = max(
            360, available.height() - frame_extra_height - safe_margin * 2
        )
        target_width = min(1280, max_client_width)
        target_height = min(800, max_client_height)

        # Keep the normal minimum where space permits, but never exceed the screen.
        self.setMinimumSize(min(900, target_width), min(600, target_height))
        self.resize(target_width, target_height)

        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        left = max(
            available.left() + safe_margin,
            min(frame.left(), available.right() - frame.width() - safe_margin + 1),
        )
        top = max(
            available.top() + safe_margin,
            min(frame.top(), available.bottom() - frame.height() - safe_margin + 1),
        )
        self.move(left, top)

    def _saved_theme(self) -> str:
        """Return the persisted UI theme, falling back to the light theme."""
        from db.models import Config

        theme = Config.get_or_none(Config.key == 'theme')
        return theme.value if theme and theme.value in {'light', 'dark'} else 'light'

    def _load_stylesheet(self, theme: str = 'light'):
        style_name = 'dark_styles.qss' if theme == 'dark' else 'styles.qss'
        style_path = os.path.join(os.path.dirname(__file__), style_name)
        if os.path.exists(style_path):
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
