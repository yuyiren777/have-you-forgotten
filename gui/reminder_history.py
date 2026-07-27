"""提醒记录页 — 查看已提醒和已过期的日程"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QTabWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from gui.components.schedule_card import ScheduleCard
from db.models import Schedule, ReminderLog


class ReminderHistoryPage(QWidget):
    """提醒记录页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('ReminderHistoryPage')
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel('提醒记录')
        title.setObjectName('PageTitle')
        layout.addWidget(title)
        subtitle = QLabel('回顾已触发、已过期和已完成的事项')
        subtitle.setObjectName('PageSubtitle')
        layout.addWidget(subtitle)
        layout.addSpacing(4)

        # 标签页切换
        self.tabs = QTabWidget()
        self._reminded_tab = QScrollArea()
        self._reminded_tab.setWidgetResizable(True)
        self._expired_tab = QScrollArea()
        self._expired_tab.setWidgetResizable(True)
        self._completed_tab = QScrollArea()
        self._completed_tab.setWidgetResizable(True)

        self.tabs.addTab(self._reminded_tab, '已提醒')
        self.tabs.addTab(self._expired_tab, '已过期')
        self.tabs.addTab(self._completed_tab, '已完成')

        # 初始化标签页容器
        self.reminded_widget = QWidget()
        self.reminded_layout = QVBoxLayout(self.reminded_widget)
        self.reminded_layout.setSpacing(8)
        self.reminded_layout.addStretch()
        self._reminded_tab.setWidget(self.reminded_widget)

        self.expired_widget = QWidget()
        self.expired_layout = QVBoxLayout(self.expired_widget)
        self.expired_layout.setSpacing(8)
        self.expired_layout.addStretch()
        self._expired_tab.setWidget(self.expired_widget)

        self.completed_widget = QWidget()
        self.completed_layout = QVBoxLayout(self.completed_widget)
        self.completed_layout.setSpacing(8)
        self.completed_layout.addStretch()
        self._completed_tab.setWidget(self.completed_widget)

        layout.addWidget(self.tabs, 1)

    def refresh(self):
        """刷新所有标签页"""
        self._refresh_tab('reminded', self.reminded_layout)
        self._refresh_tab('expired', self.expired_layout)
        self._refresh_tab('completed', self.completed_layout)

    def _refresh_tab(self, status: str, container_layout):
        # 清除旧内容
        for i in reversed(range(container_layout.count())):
            widget = container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        schedules = list(Schedule.select().where(
            Schedule.status == status
        ).order_by(Schedule.date.desc()))

        if not schedules:
            empty = QLabel('这里还没有记录')
            empty.setObjectName('EmptyState')
            empty.setMinimumHeight(220)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(empty)
        else:
            for s in schedules:
                card = ScheduleCard(s)
                if status != 'expired':
                    card.status_changed.connect(self._on_status_change)
                    card.deleted.connect(self._on_delete)
                container_layout.addWidget(card)

        container_layout.addStretch()

    def _on_status_change(self, schedule_id: int, new_status: str):
        Schedule.update(status=new_status).where(Schedule.id == schedule_id).execute()
        self.refresh()

    def _on_delete(self, schedule_id: int):
        Schedule.delete_by_id(schedule_id)
        self.refresh()
