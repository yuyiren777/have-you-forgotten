from unittest.mock import Mock, patch

import core.reminder as reminder


@patch("core.reminder.ReminderLog.create")
@patch("core.reminder.Schedule")
def test_undated_pending_items_are_notified_without_changing_status(schedule_model, create_log):
    schedule = Mock(id=1, title="理发")
    schedule_model.select.return_value.where.return_value = [schedule]
    notify = Mock()
    previous_notify = reminder.on_windows_notify
    previous_tray = reminder.on_alert_tray
    reminder.on_windows_notify = notify
    reminder.on_alert_tray = Mock()
    try:
        reminder._remind_undated_on_start()
    finally:
        reminder.on_windows_notify = previous_notify
        reminder.on_alert_tray = previous_tray

    notify.assert_called_once()
    create_log.assert_called_once()
    schedule.save.assert_not_called()
