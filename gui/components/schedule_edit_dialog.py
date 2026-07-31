"""Schedule correction dialog shared by overview and management pages."""

import datetime

from PyQt5.QtCore import QDate, Qt, QTime
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from db.database import db
from db.models import ReminderLog, Schedule
from gui.components.modern_checkbox import ModernCheckBox


class ScheduleEditDialog(QDialog):
    """Create a schedule or correct fields after AI recognition."""

    def __init__(self, schedule=None, parent=None):
        super().__init__(parent)
        self.schedule = schedule
        self.is_new = schedule is None
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setObjectName("ScheduleEditDialog")
        self.setWindowTitle("手动添加日程" if self.is_new else "修正日程")
        self.setMinimumWidth(520)
        self._setup_ui()
        self._load_schedule()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        self.heading = QLabel("手动添加日程" if self.is_new else "修正识别结果")
        self.heading.setObjectName("EditDialogTitle")
        layout.addWidget(self.heading)
        hint_text = (
            "直接填写日程信息；不确定日期或时间时，可取消对应选项。"
            if self.is_new
            else "可手动修改日期、时间和地点；未设置的项目取消勾选即可。"
        )
        self.hint = QLabel(hint_text)
        self.hint.setObjectName("EditDialogHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("日程标题")
        self.title_input.setMaxLength(512)
        form.addRow("标题", self.title_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("未设置地点时可留空")
        self.location_input.setMaxLength(512)
        form.addRow("地点", self.location_input)

        self.date_check = ModernCheckBox("设置日期")
        self.date_check.toggled.connect(self._sync_field_states)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("日期", self._field_row(self.date_check, self.date_edit))

        self.start_check = ModernCheckBox("设置开始时间")
        self.start_check.toggled.connect(self._sync_field_states)
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        form.addRow("开始", self._field_row(self.start_check, self.start_time_edit))

        self.end_check = ModernCheckBox("设置结束时间")
        self.end_check.toggled.connect(self._sync_field_states)
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm")
        form.addRow("结束", self._field_row(self.end_check, self.end_time_edit))
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("添加日程" if self.is_new else "保存修改")
        save_button.setObjectName("PrimaryButton")
        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("取消")
        cancel_button.setObjectName("SecondaryButton")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    @staticmethod
    def _field_row(toggle: ModernCheckBox, editor: QWidget) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(toggle)
        layout.addWidget(editor, 1)
        return row

    def _load_schedule(self):
        schedule = self.schedule
        self.title_input.setText(schedule.title or "" if schedule else "")
        self.location_input.setText(schedule.location or "" if schedule else "")

        self.date_check.setChecked(self.is_new or schedule.date is not None)
        initial_date = schedule.date if schedule and schedule.date else datetime.date.today()
        self.date_edit.setDate(QDate(initial_date.year, initial_date.month, initial_date.day))

        self.start_check.setChecked(schedule is not None and schedule.start_time is not None)
        start_time = schedule.start_time if schedule and schedule.start_time else datetime.time(9, 0)
        self.start_time_edit.setTime(QTime(start_time.hour, start_time.minute))

        self.end_check.setChecked(schedule is not None and schedule.end_time is not None)
        end_time = schedule.end_time if schedule and schedule.end_time else datetime.time(10, 0)
        self.end_time_edit.setTime(QTime(end_time.hour, end_time.minute))
        self._sync_field_states()

    def _sync_field_states(self):
        has_date = self.date_check.isChecked()
        has_start = has_date and self.start_check.isChecked()
        self.date_edit.setEnabled(has_date)
        self.start_check.setEnabled(has_date)
        self.start_time_edit.setEnabled(has_start)
        self.end_check.setEnabled(has_start)
        self.end_time_edit.setEnabled(has_start and self.end_check.isChecked())

    def changes(self) -> dict:
        has_date = self.date_check.isChecked()
        has_start = has_date and self.start_check.isChecked()
        has_end = has_start and self.end_check.isChecked()
        return {
            "title": self.title_input.text().strip(),
            "location": self.location_input.text().strip() or None,
            "date": self.date_edit.date().toPyDate() if has_date else None,
            "start_time": self.start_time_edit.time().toPyTime() if has_start else None,
            "end_time": self.end_time_edit.time().toPyTime() if has_end else None,
        }

    def accept(self):
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "缺少标题", "日程标题不能为空。")
            self.title_input.setFocus()
            return
        super().accept()


def apply_schedule_edits(schedule, changes: dict) -> bool:
    """Persist corrections and reset reminder state when timing changed."""
    old_timing = (schedule.date, schedule.start_time, schedule.end_time)
    new_timing = (changes["date"], changes["start_time"], changes["end_time"])
    timing_changed = old_timing != new_timing

    with db.atomic():
        schedule.title = changes["title"]
        schedule.location = changes["location"]
        schedule.date, schedule.start_time, schedule.end_time = new_timing
        schedule.updated_at = datetime.datetime.now()
        if timing_changed:
            ReminderLog.delete().where(ReminderLog.schedule == schedule.id).execute()
            if schedule.status in {"reminded", "expired"}:
                schedule.status = "pending"
                schedule.reminded_at = None
        schedule.save()
    return timing_changed


def create_schedule_from_changes(changes: dict):
    """Persist a manually entered schedule using the same normalized fields."""
    with db.atomic():
        return Schedule.create(
            title=changes["title"],
            location=changes["location"],
            date=changes["date"],
            start_time=changes["start_time"],
            end_time=changes["end_time"],
        )


def open_schedule_editor(parent, schedule_id: int) -> bool:
    """Open the shared editor and return whether changes were saved."""
    schedule = Schedule.get_by_id(schedule_id)
    dialog = ScheduleEditDialog(schedule, parent)
    if dialog.exec_() != QDialog.Accepted:
        return False
    apply_schedule_edits(schedule, dialog.changes())
    return True


def open_schedule_creator(parent) -> bool:
    """Open the manual-entry dialog and return whether a schedule was added."""
    dialog = ScheduleEditDialog(parent=parent)
    if dialog.exec_() != QDialog.Accepted:
        return False
    create_schedule_from_changes(dialog.changes())
    return True
