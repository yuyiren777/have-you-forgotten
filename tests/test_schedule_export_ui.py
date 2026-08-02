import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from gui.schedule_list import ScheduleListPage


def test_export_button_explains_selection_scope():
    app = QApplication.instance() or QApplication([])
    page = ScheduleListPage()

    assert page.export_btn.text() == "导出日程"
    assert "勾选" in page.export_btn.toolTip()
    assert not page.export_btn.isEnabled()

    page.deleteLater()
    app.processEvents()


def test_selected_schedules_are_exported_to_chosen_format(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = ScheduleListPage()
    page._visible_schedule_ids = [7, 8]
    page._selected_schedule_ids = {8}
    output = str(tmp_path / "所选日程.csv")
    schedule = SimpleNamespace(id=8)
    query = Mock()
    query.where.return_value = query
    query.order_by.return_value = [schedule]

    with patch(
        "gui.schedule_list.QFileDialog.getSaveFileName",
        return_value=(output, "CSV 表格文件 (*.csv)"),
    ), patch("gui.schedule_list.Schedule.select", return_value=query), patch(
        "gui.schedule_list.export_schedules"
    ) as export, patch("gui.schedule_list.ToastNotification.show_notification"):
        page._export_schedules()

    export.assert_called_once_with([schedule], output, "csv")

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
        page._export_schedules()

    select.assert_not_called()
    export.assert_not_called()

    page.deleteLater()
    app.processEvents()


def test_switching_format_replaces_the_previous_extension(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = ScheduleListPage()
    page._visible_schedule_ids = [7]
    chosen_path = str(tmp_path / "日程导出.ics")
    expected_path = str(tmp_path / "日程导出.csv")
    schedule = SimpleNamespace(id=7)
    query = Mock()
    query.where.return_value = query
    query.order_by.return_value = [schedule]

    with patch(
        "gui.schedule_list.QFileDialog.getSaveFileName",
        return_value=(chosen_path, "CSV 表格文件 (*.csv)"),
    ), patch("gui.schedule_list.Schedule.select", return_value=query), patch(
        "gui.schedule_list.export_schedules"
    ) as export, patch("gui.schedule_list.ToastNotification.show_notification"):
        page._export_schedules()

    export.assert_called_once_with([schedule], expected_path, "csv")

    page.deleteLater()
    app.processEvents()
