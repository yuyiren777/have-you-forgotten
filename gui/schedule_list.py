"""所有日程列表页 — 搜索、筛选、管理"""
import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox, QFrame, QFileDialog, QStyle,
    QMenu
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QFont

from gui.components.schedule_card import ScheduleCard
from gui.components.modern_checkbox import ModernCheckBox
from gui.components.schedule_edit_dialog import open_schedule_editor
from gui.components.toast_notification import ToastNotification
from db.database import db
from db.models import ReminderLog, Schedule
from core.exporter import export_schedules


class ScheduleListPage(QWidget):
    """所有日程管理页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('ScheduleListPage')
        self._selected_schedule_ids = set()
        self._visible_schedule_ids = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title = QLabel('所有日程')
        title.setObjectName('PageTitle')
        header_text.addWidget(title)
        subtitle = QLabel('搜索、筛选并管理识别到的全部安排')
        subtitle.setObjectName('PageSubtitle')
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()
        layout.addLayout(header)
        layout.addSpacing(4)

        toolbar_card = QFrame()
        toolbar_card.setObjectName('ToolbarCard')
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setContentsMargins(12, 10, 12, 10)
        toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索日程标题')
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input, 1)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['全部', '待处理', '已提醒', '已完成', '已过期'])
        self.filter_combo.setMinimumWidth(132)
        self.filter_combo.setMinimumHeight(36)
        self.filter_combo.currentTextChanged.connect(self._on_search)
        toolbar.addWidget(self.filter_combo)

        layout.addWidget(toolbar_card)

        # 批量操作
        batch_layout = QHBoxLayout()
        self.count_label = QLabel('共 0 条')
        self.count_label.setObjectName('CountLabel')
        batch_layout.addWidget(self.count_label)
        batch_layout.addStretch()

        self.export_btn = QPushButton('导出日程')
        self.export_btn.setObjectName('SecondaryButton')
        self.export_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.export_btn.setToolTip('有勾选时导出勾选日程，否则导出当前筛选结果')
        self.export_btn.setEnabled(False)
        # Qt's menu indicator can overlap the last character at high DPI unless
        # the button reserves more room than its default size hint.
        self.export_btn.setMinimumWidth(176)
        export_menu = QMenu(self.export_btn)
        excel_action = export_menu.addAction('Excel 表格（推荐，适合查看和整理）')
        html_action = export_menu.addAction('网页清单（可直接打开或打印）')
        excel_action.triggered.connect(lambda: self._export_schedules('xlsx'))
        html_action.triggered.connect(lambda: self._export_schedules('html'))
        self.export_btn.setMenu(export_menu)
        batch_layout.addWidget(self.export_btn)

        self.select_all_box = ModernCheckBox('全选当前列表')
        self.select_all_box.toggled.connect(self._set_all_selected)
        batch_layout.addWidget(self.select_all_box)

        self.delete_selected_btn = QPushButton('删除已选 (0)')
        self.delete_selected_btn.setObjectName('DangerButton')
        self.delete_selected_btn.setEnabled(False)
        self.delete_selected_btn.clicked.connect(self._delete_selected)
        batch_layout.addWidget(self.delete_selected_btn)

        self.clear_expired_btn = QPushButton('清理过期日程')
        self.clear_expired_btn.setObjectName('DangerButton')
        self.clear_expired_btn.clicked.connect(self._clear_expired)
        batch_layout.addWidget(self.clear_expired_btn)

        layout.addLayout(batch_layout)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.list_layout = QVBoxLayout(scroll_widget)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        scroll.setWidget(scroll_widget)

        layout.addWidget(scroll, 1)

    def _on_search(self):
        self.refresh()

    def refresh(self):
        """刷新列表"""
        # 清除旧卡片
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 构建查询
        search_text = self.search_input.text().strip()
        filter_status = self.filter_combo.currentText()

        query = Schedule.select()

        if filter_status == '待处理':
            query = query.where(Schedule.status == 'pending')
        elif filter_status == '已提醒':
            query = query.where(Schedule.status == 'reminded')
        elif filter_status == '已完成':
            query = query.where(Schedule.status == 'completed')
        elif filter_status == '已过期':
            query = query.where(Schedule.status == 'expired')

        if search_text:
            query = query.where(Schedule.title.contains(search_text))

        schedules = list(query.order_by(Schedule.date.asc(), Schedule.start_time.asc()))
        self._visible_schedule_ids = [schedule.id for schedule in schedules]
        self._update_selection_controls()
        expired_count = Schedule.select().where(self._expired_filter()).count()
        self.clear_expired_btn.setText(f'清理过期日程 ({expired_count})')
        self.clear_expired_btn.setEnabled(expired_count > 0)
        self.count_label.setText(f'共 {len(schedules)} 条')

        if not schedules:
            empty = QFrame()
            empty.setObjectName('EmptyState')
            empty.setMinimumHeight(240)
            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(8)
            empty_title = QLabel('没有匹配的日程' if search_text or filter_status != '全部' else '还没有日程')
            empty_title.setObjectName('SectionTitle')
            empty_layout.addWidget(empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
            empty_hint = QLabel('尝试调整搜索或筛选条件' if search_text or filter_status != '全部' else '在概览页添加文字或图片后，日程会自动归档到这里。')
            empty_hint.setObjectName('SectionHint')
            empty_layout.addWidget(empty_hint, alignment=Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(empty)
        else:
            for s in schedules:
                card = ScheduleCard(s)
                card.status_changed.connect(self._on_status_change)
                card.deleted.connect(self._on_delete)
                card.edit_requested.connect(self._on_edit)
                card.selection_changed.connect(self._on_selection_changed)
                card.set_selected(s.id in self._selected_schedule_ids)
                self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def _on_status_change(self, schedule_id: int, new_status: str):
        try:
            Schedule.update(status=new_status).where(Schedule.id == schedule_id).execute()
            ToastNotification.show_notification('状态更新', f'日程已标记为"{new_status}"', self)
            self.refresh()
        except Exception as e:
            print(f'更新失败: {e}')

    def _on_delete(self, schedule_id: int):
        reply = QMessageBox.question(
            self, '确认删除', '确定要删除这条日程吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._delete_schedule_ids([schedule_id])
                self.refresh()
            except Exception as e:
                print(f'删除失败: {e}')

    def _on_selection_changed(self, schedule_id: int, selected: bool):
        if selected:
            self._selected_schedule_ids.add(schedule_id)
        else:
            self._selected_schedule_ids.discard(schedule_id)
        self._update_selection_controls()

    def _update_selection_controls(self):
        self._selected_schedule_ids.intersection_update(self._visible_schedule_ids)
        selected_count = len(self._selected_schedule_ids)
        self.delete_selected_btn.setText(f'删除已选 ({selected_count})')
        self.delete_selected_btn.setEnabled(selected_count > 0)
        self.select_all_box.blockSignals(True)
        self.select_all_box.setChecked(
            bool(self._visible_schedule_ids) and selected_count == len(self._visible_schedule_ids)
        )
        self.select_all_box.blockSignals(False)
        self.export_btn.setEnabled(bool(self._visible_schedule_ids))

    def _set_all_selected(self, selected: bool):
        if selected:
            self._selected_schedule_ids.update(self._visible_schedule_ids)
        else:
            self._selected_schedule_ids.difference_update(self._visible_schedule_ids)
        self.refresh()

    def _delete_selected(self):
        selected_ids = sorted(self._selected_schedule_ids)
        if not selected_ids:
            return
        reply = QMessageBox.question(
            self, '删除已选日程', f'确定要删除选中的 {len(selected_ids)} 条日程吗？此操作不可撤销。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._delete_schedule_ids(selected_ids)
                self._selected_schedule_ids.clear()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, '删除失败', f'无法删除所选日程：{e}')

    @staticmethod
    def _expired_filter():
        overdue_pending = (
            (Schedule.status == 'pending') &
            Schedule.date.is_null(False) &
            (Schedule.date < datetime.date.today())
        )
        return (Schedule.status == 'expired') | overdue_pending

    @staticmethod
    def _delete_schedule_ids(schedule_ids):
        ids = list(schedule_ids)
        if not ids:
            return 0
        with db.atomic():
            ReminderLog.delete().where(ReminderLog.schedule.in_(ids)).execute()
            return Schedule.delete().where(Schedule.id.in_(ids)).execute()

    def _on_edit(self, schedule_id: int):
        if open_schedule_editor(self, schedule_id):
            self.refresh()

    def _export_schedules(self, export_format: str):
        schedule_ids = sorted(self._selected_schedule_ids) or self._visible_schedule_ids
        if not schedule_ids:
            return

        if export_format == 'xlsx':
            default_name = f'日程清单-{datetime.date.today():%Y%m%d}.xlsx'
            file_filter = 'Excel 表格 (*.xlsx)'
        else:
            default_name = f'日程清单-{datetime.date.today():%Y%m%d}.html'
            file_filter = '网页清单 (*.html)'
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            '导出日程',
            default_name,
            file_filter,
        )
        if not file_path:
            return

        extension = f'.{export_format}'
        current_suffix = Path(file_path).suffix.lower()
        if current_suffix in {'.xlsx', '.html'} and current_suffix != extension:
            file_path = str(Path(file_path).with_suffix(extension))
        elif not file_path.lower().endswith(extension):
            file_path += extension

        try:
            schedules = list(
                Schedule.select()
                .where(Schedule.id.in_(schedule_ids))
                .order_by(Schedule.date.asc(), Schedule.start_time.asc())
            )
            export_schedules(schedules, file_path, export_format)
            scope = '所选' if self._selected_schedule_ids else '当前列表中的'
            open_now = QMessageBox.question(
                self,
                '导出完成',
                f'已将{scope} {len(schedules)} 条日程导出到：\n{file_path}\n\n是否立即打开？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if open_now == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as error:
            QMessageBox.critical(self, '导出失败', f'无法导出日程：{error}')

    def _clear_expired(self):
        reply = QMessageBox.question(
            self, '清理过期日程', '确定要删除所有已过期的日程吗？此操作不可撤销。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                expired_filter = self._expired_filter()
                expired_ids = Schedule.select(Schedule.id).where(expired_filter)
                deleted_count = self._delete_schedule_ids(expired_ids)
                self.refresh()
                ToastNotification.show_notification('清理完成', f'已清理 {deleted_count} 条过期日程。', self)
            except Exception as e:
                QMessageBox.critical(self, '清理失败', f'无法清理过期日程：{e}')
