import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtTest import QSignalSpy

from gui.settings_page import SettingsPage
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
