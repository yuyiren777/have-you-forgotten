import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox

from gui.schedule_list import ScheduleListPage


def test_export_menu_uses_familiar_user_facing_formats():
    app = QApplication.instance() or QApplication([])
    page = ScheduleListPage()
    actions = [action.text() for action in page.export_btn.menu().actions()]

    assert page.export_btn.text() == "导出日程"
    assert actions == [
        "Excel 表格（推荐，适合查看和整理）",
        "网页清单（可直接打开或打印）",
    ]
    assert not any("ICS" in action or "CSV" in action for action in actions)

    page.deleteLater()
    app.processEvents()


def test_selected_schedules_are_exported_to_excel_and_can_be_opened(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = ScheduleListPage()
    page._visible_schedule_ids = [7, 8]
    page._selected_schedule_ids = {8}
    output = str(tmp_path / "所选日程.xlsx")
    schedule = SimpleNamespace(id=8)
    query = Mock()
    query.where.return_value = query
    query.order_by.return_value = [schedule]

    with patch(
        "gui.schedule_list.QFileDialog.getSaveFileName",
        return_value=(output, "Excel 表格 (*.xlsx)"),
    ), patch("gui.schedule_list.Schedule.select", return_value=query), patch(
        "gui.schedule_list.export_schedules"
    ) as export, patch(
        "gui.schedule_list.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch("gui.schedule_list.QDesktopServices.openUrl") as open_url:
        page._export_schedules("xlsx")

    export.assert_called_once_with([schedule], output, "xlsx")
    assert Path(open_url.call_args.args[0].toLocalFile()) == Path(output)

    page.deleteLater()
    app.processEvents()


def test_cancelled_export_does_not_query_or_write():
    app = QApplication.instance() or QApplication([])
    page = ScheduleListPage()
    page._visible_schedule_ids = [7]

    with patch(
        "gui.schedule_list.QFileDialog.getSaveFileName", return_value=("", "")
    ), patch("gui.schedule_list.Schedule.select") as select, patch(
        "gui.schedule_list.export_schedules"
    ) as export:
        page._export_schedules("html")

    select.assert_not_called()
    export.assert_not_called()

    page.deleteLater()
    app.processEvents()
