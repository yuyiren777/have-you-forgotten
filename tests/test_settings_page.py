import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtTest import QSignalSpy

from gui.settings_page import SettingsPage
from gui.components.modern_checkbox import ModernCheckBox
from gui.home_page import HomePage
from gui.main_window import MainWindow


class SettingsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        with patch.object(SettingsPage, "_load_config"):
            self.page = SettingsPage()

    def tearDown(self):
        self.page.deleteLater()

    def test_only_current_step_is_shown(self):
        self.assertEqual(self.page.step_stack.currentIndex(), 0)
        self.assertEqual(self.page._step_indicators[0].property("stepState"), "active")
        self.assertEqual(self.page._step_indicators[1].property("stepState"), "pending")

        self.page.api_key_input.setText("test-key")
        self.page._next_step()

        self.assertEqual(self.page.step_stack.currentIndex(), 1)
        self.assertEqual(self.page._step_indicators[0].property("stepState"), "complete")
        self.assertEqual(self.page._step_indicators[1].property("stepState"), "active")
        self.assertTrue(self.page.back_btn.isVisibleTo(self.page))

    def test_optional_notification_steps_can_be_skipped(self):
        self.page._show_step(2)
        self.page.wechat_service_combo.setCurrentIndex(0)
        self.page._next_step()

        self.assertEqual(self.page.step_stack.currentIndex(), 3)
        self.assertEqual(self.page.next_btn.text(), "保存设置")

    def test_only_model_api_key_is_required(self):
        self.page.api_key_input.setText("test-key")
        self.page.wechat_service_combo.setCurrentIndex(1)
        self.page.email_service_combo.setCurrentIndex(1)

        self.assertTrue(self.page._validate_step(0))
        self.assertTrue(self.page._validate_step(2))
        self.assertTrue(self.page._validate_step(3))

    def test_model_mode_switches_between_unified_and_separate_fields(self):
        self.page._set_model_mode("unified")
        self.assertTrue(self.page.unified_model_input.isVisibleTo(self.page))
        self.assertFalse(self.page.text_model_input.isVisibleTo(self.page))
        self.assertFalse(self.page.image_model_input.isVisibleTo(self.page))

        self.page._set_model_mode("separate")
        self.assertFalse(self.page.unified_model_input.isVisibleTo(self.page))
        self.assertTrue(self.page.text_model_input.isVisibleTo(self.page))
        self.assertTrue(self.page.image_model_input.isVisibleTo(self.page))

    def test_model_settings_use_a_visible_vertical_scrollbar(self):
        self.assertTrue(self.page.model_scroll.widgetResizable())
        self.assertEqual(
            self.page.model_scroll.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn,
        )
        self.assertEqual(
            self.page.model_scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

    def test_autostart_uses_high_visibility_checkbox(self):
        self.assertIsInstance(self.page.autostart_check, ModernCheckBox)
        self.assertGreaterEqual(self.page.autostart_check.minimumHeight(), 42)
        self.assertTrue(self.page.autostart_check.toolTip())

    def test_separate_model_names_are_saved_independently(self):
        self.page._set_model_mode("separate")
        self.page.text_model_input.setText("text-model")
        self.page.image_model_input.setText("vision-model")

        data = self.page._config_data()

        self.assertEqual(data["model_mode"], "separate")
        self.assertEqual(data["text_model_name"], "text-model")
        self.assertEqual(data["image_model_name"], "vision-model")
        self.assertEqual(data["model_name"], "")

    def test_unified_model_keeps_legacy_model_key_in_sync(self):
        self.page._set_model_mode("unified")
        self.page.unified_model_input.setText("one-vision-model")

        data = self.page._config_data()

        self.assertEqual(data["model_mode"], "unified")
        self.assertEqual(data["unified_model_name"], "one-vision-model")
        self.assertEqual(data["model_name"], "one-vision-model")

    def test_reminder_stages_save_independently(self):
        self.page.first_days_spin.setValue(300)
        self.page.first_hours_spin.setValue(5)
        self.page.first_minutes_spin.setValue(12)
        self.page.second_days_spin.setValue(7)
        self.page.second_hours_spin.setValue(1)
        self.page.second_minutes_spin.setValue(0)
        self.page.final_minutes_spin.setValue(30)

        data = self.page._config_data()
        self.assertEqual(data["reminder_first_days"], "300")
        self.assertEqual(data["reminder_second_days"], "7")
        self.assertEqual(data["reminder_final_minutes"], "30")
        self.assertEqual(data["reminder_advance"], "30")

    def test_reminder_stage_order_is_validated(self):
        self.page.first_minutes_spin.setValue(20)
        self.page.second_minutes_spin.setValue(0)
        self.page.final_minutes_spin.setValue(30)

        with patch.object(self.page, "_show_required", return_value=False) as show_required:
            self.assertFalse(self.page._validate_step(1))

        show_required.assert_called_once()

    def test_selected_theme_is_included_in_saved_config(self):
        with patch("gui.settings_page.get_db"), patch(
            "gui.settings_page.Config.replace"
        ) as replace:
            self.page.theme_combo.setCurrentIndex(self.page.theme_combo.findData("dark"))

        self.assertEqual(self.page._config_data()["theme"], "dark")
        replace.assert_called_once_with(key="theme", value="dark")

    def test_qq_email_address_uses_qq_number_format(self):
        self.assertTrue(self.page._is_qq_email_address("123456@qq.com"))
        self.assertFalse(self.page._is_qq_email_address("name@qq.com"))
        self.assertFalse(self.page._is_qq_email_address("123456@qq.com.cn"))

    def test_qq_email_format_is_shown_in_the_page_description(self):
        self.page.email_service_combo.setCurrentIndex(1)

        self.assertEqual(self.page.email_address_input.placeholderText(), "例如：123456@qq.com")

    def test_final_save_marks_setup_complete(self):
        completed = QSignalSpy(self.page.setup_completed)
        with patch.object(self.page, "_persist_config") as persist, patch(
            "gui.settings_page.QMessageBox.information"
        ):
            self.page._save_config()

        persist.assert_called_once_with(mark_complete=True)
        self.assertEqual(len(completed), 1)

    def test_home_blocks_recognition_until_setup_is_complete(self):
        home = HomePage()
        required = QSignalSpy(home.setup_required)

        with patch("gui.home_page.is_setup_complete", return_value=False):
            home._start_process("text", "明天下午开会")

        self.assertEqual(len(required), 1)
        self.assertFalse(home._processing)
        home.deleteLater()

    def test_home_model_label_refreshes_without_restart(self):
        with patch("gui.home_page.get_model_name", return_value="文字 old · 图片 old"):
            home = HomePage()
        self.assertEqual(home.model_label.text(), "AI 模型  ·  文字 old · 图片 old")

        with patch("gui.home_page.get_model_name", return_value="文字 new · 图片 vision"):
            home.refresh_model_label()

        self.assertEqual(home.model_label.text(), "AI 模型  ·  文字 new · 图片 vision")
        self.assertEqual(home.model_label.toolTip(), "文字 new · 图片 vision")
        home.deleteLater()

    def test_switching_to_overview_refreshes_model_before_schedules(self):
        window = Mock()
        window.nav_buttons = []
        window.home_page = Mock()
        window.schedule_page = Mock()
        window.reminder_page = Mock()
        calls = []
        window.home_page.refresh_model_label.side_effect = lambda: calls.append("model")
        window.home_page.refresh_schedules.side_effect = lambda: calls.append("schedules")

        MainWindow._switch_page(window, 0)

        self.assertEqual(calls, ["model", "schedules"])

    def test_initial_window_frame_stays_inside_available_screen(self):
        window = QMainWindow()
        window.resize(1280, 800)
        window.show()
        self.app.processEvents()

        MainWindow._fit_and_center_on_screen(window)

        available = window.screen().availableGeometry()
        frame = window.frameGeometry()
        self.assertGreaterEqual(frame.left(), available.left())
        self.assertGreaterEqual(frame.top(), available.top())
        self.assertLessEqual(frame.right(), available.right())
        self.assertLessEqual(frame.bottom(), available.bottom())
        window.close()


if __name__ == "__main__":
    unittest.main()
