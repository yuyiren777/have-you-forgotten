"""日程卡片组件 — 用于列表展示"""
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QWidget
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QAction

from gui.components.modern_checkbox import ModernCheckBox
from utils.date_parser import format_remaining_time, format_schedule_time
from utils.schedule_content import clean_optional_text, readable_notes


class ScheduleCard(QFrame):
    """日程展示卡片"""

    RELATIVE_TIME_REFRESH_MS = 30_000

    status_changed = pyqtSignal(int, str)  # schedule_id, new_status
    deleted = pyqtSignal(int)  # schedule_id
    edit_requested = pyqtSignal(int)  # schedule_id
    selection_changed = pyqtSignal(int, bool)  # schedule_id, selected

    URGENCY_COLORS = {
        0: '#4CAF50',  # 普通 - 绿色
        1: '#FF9800',  # 重要 - 橙色
        2: '#F44336',  # 紧急 - 红色
    }
    def __init__(self, schedule, parent=None, show_delete_button: bool = False):
        super().__init__(parent)
        self.schedule = schedule
        self.show_delete_button = show_delete_button
        self.remaining_label = None
        self._remaining_timer = None
        self.setObjectName('ScheduleCard')
        self._setup_ui()

    def _setup_ui(self):
        s = self.schedule
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        urgency_bar = QFrame()
        urgency_bar.setObjectName('UrgencyBar')
        urgency_bar.setFixedWidth(4)
        urgency_bar.setStyleSheet(
            f"background: {self.URGENCY_COLORS.get(s.urgency, '#2B7A78')}; border-radius: 2px;"
        )
        outer.addWidget(urgency_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)
        outer.addWidget(content, 1)

        # 第一行：标题 + 紧急标记 + 状态
        row1 = QHBoxLayout()
        self.select_box = ModernCheckBox()
        self.select_box.setObjectName('ScheduleSelect')
        self.select_box.setToolTip('选择日程')
        self.select_box.toggled.connect(lambda checked: self.selection_changed.emit(s.id, checked))
        row1.addWidget(self.select_box)
        title_label = QLabel(s.title)
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        row1.addWidget(title_label, 1)

        status_map = {
            'pending': '待处理',
            'reminded': '已提醒',
            'completed': '已完成',
            'expired': '已过期',
        }
        status_label = QLabel(status_map.get(s.status, s.status))
        status_label.setObjectName('StatusBadge')
        row1.addWidget(status_label)
        layout.addLayout(row1)

        # 第二行：时间 + 剩余时间
        row2 = QHBoxLayout()
        time_str = format_schedule_time(s)
        time_label = QLabel(time_str)
        time_label.setStyleSheet('color: #40515D; font-size: 12pt; font-weight: 600;')
        row2.addWidget(time_label)

        if s.status == 'pending':
            self.remaining_label = QLabel()
            self.remaining_label.setObjectName('RemainingTimeLabel')
            row2.addWidget(self.remaining_label)
            self._refresh_remaining_time()

            self._remaining_timer = QTimer(self)
            self._remaining_timer.setTimerType(Qt.TimerType.CoarseTimer)
            self._remaining_timer.setInterval(self.RELATIVE_TIME_REFRESH_MS)
            self._remaining_timer.timeout.connect(self._refresh_remaining_time)
            self._remaining_timer.start()

        row2.addStretch()
        layout.addLayout(row2)

        # 第三行：地点 + 操作按钮
        row3 = QHBoxLayout()
        location = clean_optional_text(s.location)
        if location:
            loc_label = QLabel(f'地点  {location}')
            loc_label.setStyleSheet('color: #71808C; font-size: 11pt;')
            row3.addWidget(loc_label)

        notes = readable_notes(s.notes)
        if notes:
            desc_label = QLabel(f'备注  {notes[:50]}')
            desc_label.setStyleSheet('color: #71808C; font-size: 11pt;')
            desc_label.setToolTip(notes)
            row3.addWidget(desc_label)

        row3.addStretch()

        # 操作按钮
        edit_btn = QPushButton('编辑')
        edit_btn.setObjectName('SmallButton')
        edit_btn.setToolTip('编辑日程内容、时间、紧急度和备注')
        edit_btn.setFixedHeight(28)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(s.id))
        row3.addWidget(edit_btn)

        if s.status == 'pending' or s.status == 'reminded':
            done_btn = QPushButton('标记完成')
            done_btn.setObjectName('SmallButton')
            done_btn.setFixedHeight(28)
            done_btn.clicked.connect(lambda: self.status_changed.emit(s.id, 'completed'))
            row3.addWidget(done_btn)

        if s.status == 'completed':
            undo_btn = QPushButton('恢复待办')
            undo_btn.setObjectName('SmallButton')
            undo_btn.setFixedHeight(28)
            undo_btn.clicked.connect(lambda: self.status_changed.emit(s.id, 'pending'))
            row3.addWidget(undo_btn)

        if self.show_delete_button:
            delete_btn = QPushButton('删除')
            delete_btn.setObjectName('DangerButton')
            delete_btn.setToolTip('删除这条日程')
            delete_btn.setFixedHeight(28)
            delete_btn.clicked.connect(lambda: self.deleted.emit(s.id))
            row3.addWidget(delete_btn)

        layout.addLayout(row3)

    def _refresh_remaining_time(self):
        """Update only the relative-time text without rebuilding the card."""
        if self.remaining_label is None:
            return
        remaining = format_remaining_time(
            self.schedule.date,
            self.schedule.start_time,
        )
        urgent = (
            '分钟' in remaining
            or remaining in {'现在', '已过期'}
            or remaining.startswith('已开始')
        )
        color = '#B34D4D' if urgent else '#71808C'
        self.remaining_label.setText(remaining)
        self.remaining_label.setStyleSheet(f'color: {color}; font-size: 11pt;')

    def set_selected(self, selected: bool):
        self.select_box.blockSignals(True)
        self.select_box.setChecked(selected)
        self.select_box.blockSignals(False)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        edit_action = QAction('编辑', self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.schedule.id))
        menu.addAction(edit_action)

        menu.addSeparator()

        delete_action = QAction('删除', self)
        delete_action.triggered.connect(lambda: self.deleted.emit(self.schedule.id))
        menu.addAction(delete_action)

        menu.exec_(event.globalPos())
