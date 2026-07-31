"""首页 — 输入区域 + 今日日程 + 近期时间线"""
import datetime
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame,
    QMessageBox, QApplication, QPushButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from gui.components.input_card import InputCard
from gui.components.image_drop_zone import ImageDropZone
from gui.components.schedule_card import ScheduleCard
from gui.components.schedule_edit_dialog import open_schedule_creator, open_schedule_editor
from gui.components.shimmer_loader import ShimmerLoader
from gui.components.toast_notification import ToastNotification
from db.database import db, get_db
from db.models import Schedule, Input, ReminderLog
from core.workflow import process_input
from core.deduplicator import find_duplicate, merge_schedule
from core.api_client import get_model_name, is_setup_complete


class ProcessThread(QThread):
    """后台处理线程"""
    finished = pyqtSignal(list)   # 成功: 返回日程列表
    error = pyqtSignal(str)       # 失败: 返回错误信息
    progress = pyqtSignal(str)    # 进度信息

    def __init__(self, source_type: str, source_data, parent=None):
        super().__init__(parent)
        self.source_type = source_type  # 'text' | 'image'
        self.source_data = source_data  # str (text) or list[str] (image paths)

    def run(self):
        try:
            parsed = process_input(
                self.source_type,
                self.source_data,
                progress=self.progress.emit,
            )
            self.finished.emit(parsed)
        except Exception as e:
            self.error.emit(str(e))


class HomePage(QWidget):
    """首页"""

    setup_required = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('HomePage')
        self._processing = False
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 24)
        main_layout.setSpacing(24)

        # ===== 左侧：输入区 =====
        left_scroll = QScrollArea()
        left_scroll.setObjectName('LeftScroll')
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        left_scroll.setFixedWidth(426)

        left_panel = QFrame()
        left_panel.setObjectName('LeftPanel')
        left_panel.setMinimumWidth(390)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        page_title = QLabel('快速添加')
        page_title.setObjectName('PageTitle')
        left_layout.addWidget(page_title)

        page_subtitle = QLabel('把聊天记录、通知或截图交给 AI，自动整理成日程。')
        page_subtitle.setObjectName('PageSubtitle')
        page_subtitle.setWordWrap(True)
        left_layout.addWidget(page_subtitle)
        left_layout.addSpacing(6)

        # 模型状态提示
        self.model_label = QLabel()
        self.model_label.setObjectName('MutedLabel')
        self.model_label.setWordWrap(True)
        left_layout.addWidget(self.model_label)
        self.refresh_model_label()

        # 文字输入卡片
        self.input_card = InputCard()
        self.input_card.submit_text.connect(self._on_text_submit)
        left_layout.addWidget(self.input_card)

        # 图片拖拽区
        self.drop_zone = ImageDropZone()
        self.drop_zone.image_added.connect(lambda p: None)  # 累积在 drop_zone 内部
        left_layout.addWidget(self.drop_zone)

        # 识别按钮
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 2, 0, 0)
        self.recognize_btn = QPushButton('识别全部内容')
        self.recognize_btn.setObjectName('PrimaryButton')
        self.recognize_btn.setMinimumHeight(40)
        self.recognize_btn.clicked.connect(self._on_recognize_all)
        btn_layout.addWidget(self.recognize_btn, 1)
        left_layout.addLayout(btn_layout)

        # 加载动画（初始隐藏）
        self.loader = ShimmerLoader()
        self.loader.setVisible(False)
        left_layout.addWidget(self.loader)

        # Manual entry remains available when AI recognition is unavailable.
        manual_panel = QFrame()
        manual_panel.setObjectName('ManualAddPanel')
        manual_layout = QVBoxLayout(manual_panel)
        manual_layout.setContentsMargins(16, 14, 16, 14)
        manual_layout.setSpacing(7)
        manual_title = QLabel('手动添加')
        manual_title.setObjectName('ManualAddTitle')
        manual_layout.addWidget(manual_title)
        manual_hint = QLabel('AI 超时或识别失败时，可直接填写日期、时间和地点。')
        manual_hint.setObjectName('SectionHint')
        manual_hint.setWordWrap(True)
        manual_layout.addWidget(manual_hint)
        self.manual_add_btn = QPushButton('手动填写日程')
        self.manual_add_btn.setObjectName('SecondaryButton')
        self.manual_add_btn.setMinimumHeight(40)
        self.manual_add_btn.clicked.connect(self._on_manual_add)
        manual_layout.addWidget(self.manual_add_btn)
        left_layout.addWidget(manual_panel)

        left_layout.addStretch()

        left_scroll.setWidget(left_panel)

        # ===== 右侧：日程展示区 =====
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setObjectName('RightScroll')

        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(0, 0, 8, 0)
        self.right_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        today_title = QLabel('日程概览')
        today_title.setObjectName('PageTitle')
        header_text.addWidget(today_title)
        overview_hint = QLabel('接下来需要关注的事项')
        overview_hint.setObjectName('PageSubtitle')
        header_text.addWidget(overview_hint)
        header_row.addLayout(header_text)
        header_row.addStretch()
        self.schedule_count_label = QLabel('0 项待处理')
        self.schedule_count_label.setObjectName('CountLabel')
        header_row.addWidget(self.schedule_count_label, alignment=Qt.AlignmentFlag.AlignBottom)
        self.right_layout.addLayout(header_row)
        self.right_layout.addSpacing(6)

        # 日程卡片容器
        self.schedule_container = QVBoxLayout()
        self.schedule_container.setSpacing(8)
        self.right_layout.addLayout(self.schedule_container)

        self.right_layout.addStretch()

        right_scroll.setWidget(right_widget)
        main_layout.addWidget(left_scroll)
        main_layout.addWidget(right_scroll, 1)

    def refresh_model_label(self):
        """Show the currently saved model configuration without restarting."""
        model_name = get_model_name()
        self.model_label.setText(f'AI 模型  ·  {model_name}')
        self.model_label.setToolTip(model_name)

    def _on_text_submit(self, text: str):
        """文字提交"""
        if self._processing:
            return
        self._start_process('text', text)

    def _on_recognize_all(self):
        """识别全部（文字 + 图片）"""
        if self._processing:
            return

        text = self.input_card.text_edit.toPlainText().strip()
        images = self.drop_zone.get_images()

        if not text and not images:
            QMessageBox.information(self, '提示', '请先输入文字或添加图片')
            return

        if images and not text:
            self._start_process('image', images)
        elif text and not images:
            self._start_process('text', text)
        else:
            # 先处理图片，再处理文字
            self._start_process('image', images, extra_text=text)

    def _start_process(self, source_type: str, source_data, extra_text: str = ''):
        if not is_setup_complete():
            self.setup_required.emit()
            return
        self._processing = True
        self.recognize_btn.setDisabled(True)
        self.loader.setVisible(True)
        self.loader.set_text('正在识别中...')

        self._extra_text = extra_text
        self._current_source_type = source_type
        self._current_source_data = source_data

        self.thread = ProcessThread(source_type, source_data)
        self.thread.progress.connect(self.loader.set_progress)
        self.thread.finished.connect(self._on_process_finished)
        self.thread.error.connect(self._on_process_error)
        self.thread.start()

    def _on_process_finished(self, parsed_items: list):
        count = 0
        merged = 0

        # 保存原始输入
        source_type = self._current_source_type
        if source_type == 'text':
            inp = Input.create(type='text', content=self._current_source_data)
            inp_id = inp.id
        else:
            inp_id = None
            for img_path in (self._current_source_data if isinstance(self._current_source_data, list) else [self._current_source_data]):
                inp = Input.create(type='image', content='', image_path=img_path)
                inp_id = inp.id

        for item in parsed_items:
            item['input_id'] = inp_id
            try:
                # 查重
                dup = find_duplicate(item)
                if dup:
                    merge_schedule(dup, item)
                    merged += 1
                else:
                    Schedule.create(
                        input_id=item.get('input_id'),
                        title=item['title'],
                        description=item.get('description'),
                        date=item.get('date'),
                        start_time=item.get('start_time'),
                        end_time=item.get('end_time'),
                        location=item.get('location'),
                        notes=item.get('notes'),
                        repeat_rule=item.get('repeat_rule'),
                        urgency=item.get('urgency', 0),
                    )
                    count += 1
            except Exception as e:
                print(f'保存日程失败: {e}')

        # 如果有额外文字，接着处理
        if self._extra_text:
            self.loader.set_progress('正在处理文字...')
            self._current_source_type = 'text'
            self._current_source_data = self._extra_text
            self._extra_text = ''
            self.thread2 = ProcessThread('text', self._current_source_data)
            self.thread2.progress.connect(self.loader.set_progress)
            self.thread2.finished.connect(self._on_second_finished)
            self.thread2.error.connect(self._on_process_error)
            self.thread2.start()
            return

        self._finish_processing(count, merged)

    def _on_second_finished(self, parsed_items: list):
        count = 0
        merged = 0
        for item in parsed_items:
            try:
                dup = find_duplicate(item)
                if dup:
                    merge_schedule(dup, item)
                    merged += 1
                else:
                    Schedule.create(
                        title=item['title'],
                        description=item.get('description'),
                        date=item.get('date'),
                        start_time=item.get('start_time'),
                        end_time=item.get('end_time'),
                        location=item.get('location'),
                        notes=item.get('notes'),
                        repeat_rule=item.get('repeat_rule'),
                        urgency=item.get('urgency', 0),
                    )
                    count += 1
            except Exception as e:
                print(f'保存日程失败: {e}')

        self._finish_processing(count, merged)

    def _finish_processing(self, count: int, merged: int):
        self._processing = False
        self.recognize_btn.setDisabled(False)
        self.loader.setVisible(False)

        # 显示结果
        msg_parts = [f'✅ 新增 {count} 条日程']
        if merged:
            msg_parts.append(f'🔄 合并 {merged} 条重复日程')

        ToastNotification.show_notification(
            '识别完成',
            '\n'.join(msg_parts),
            self
        )

        # 刷新日程列表
        self.refresh_schedules()

        # 清空输入
        self.input_card.text_edit.clear()
        self.drop_zone.clear_all()

    def _on_process_error(self, error_msg: str):
        self._processing = False
        self.recognize_btn.setDisabled(False)
        self.loader.setVisible(False)

        QMessageBox.warning(self, '识别失败', f'出错了：{error_msg}\n\n请检查 API Key 和网络连接')

    def _on_manual_add(self):
        if open_schedule_creator(self):
            self.refresh_schedules()

    def refresh_schedules(self):
        """刷新日程卡片列表"""
        # 清除旧卡片
        for i in reversed(range(self.schedule_container.count())):
            widget = self.schedule_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 加载日程（按日期排序，今日优先）
        today = datetime.date.today()
        schedules = list(Schedule.select().where(
            (Schedule.status.in_(['pending', 'reminded']))
        ).order_by(Schedule.date.asc(), Schedule.start_time.asc()))
        self.schedule_count_label.setText(f'{len(schedules)} 项待处理')

        # 分组：今日 / 明天 / 未来
        today_schedules = []
        tomorrow_schedules = []
        future_schedules = []
        overdue_schedules = []
        undated_schedules = []

        for s in schedules:
            if not s.date:
                undated_schedules.append(s)
            elif s.date < today:
                overdue_schedules.append(s)
            elif s.date == today:
                today_schedules.append(s)
            elif s.date == today + datetime.timedelta(days=1):
                tomorrow_schedules.append(s)
            else:
                future_schedules.append(s)

        self._add_group('今天', today_schedules)
        self._add_group('明天', tomorrow_schedules)
        self._add_group('未来', future_schedules)
        self._add_group('已过期', overdue_schedules)
        self._add_group('未设日期', undated_schedules)

        if not schedules:
            empty = QFrame()
            empty.setObjectName('EmptyState')
            empty.setMinimumHeight(220)
            empty_layout = QVBoxLayout(empty)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(8)
            empty_title = QLabel('今天还没有安排')
            empty_title.setObjectName('SectionTitle')
            empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_title)
            empty_hint = QLabel('从左侧输入文字或添加截图，识别后的日程会显示在这里。')
            empty_hint.setObjectName('SectionHint')
            empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_hint.setWordWrap(True)
            empty_layout.addWidget(empty_hint)
            self.schedule_container.addWidget(empty)

        self.schedule_container.addStretch()

    def _add_group(self, title: str, schedules: list):
        if not schedules:
            return

        group_label = QLabel(title)
        group_font = QFont()
        group_font.setPointSize(12)
        group_font.setBold(True)
        group_label.setFont(group_font)
        group_label.setObjectName('SectionTitle')
        group_label.setStyleSheet('margin-top: 8px;')
        self.schedule_container.addWidget(group_label)

        for s in schedules:
            card = ScheduleCard(s, show_delete_button=True)
            card.status_changed.connect(self._on_status_change)
            card.edit_requested.connect(self._on_edit)
            card.deleted.connect(self._on_delete)
            self.schedule_container.addWidget(card)

    def _on_status_change(self, schedule_id: int, new_status: str):
        try:
            Schedule.update(status=new_status).where(Schedule.id == schedule_id).execute()
            self.refresh_schedules()
        except Exception as e:
            print(f'更新状态失败: {e}')

    def _on_edit(self, schedule_id: int):
        if open_schedule_editor(self, schedule_id):
            self.refresh_schedules()

    def _on_delete(self, schedule_id: int):
        reply = QMessageBox.question(
            self, '确认删除', '确定要删除这条日程吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with db.atomic():
                    ReminderLog.delete().where(ReminderLog.schedule == schedule_id).execute()
                    Schedule.delete().where(Schedule.id == schedule_id).execute()
                self.refresh_schedules()
            except Exception as e:
                QMessageBox.critical(self, '删除失败', f'无法删除这条日程：{e}')
