import datetime
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from core.workflow import parse_model_response, process_input
from utils.date_context import get_date_context


class WorkflowTests(unittest.TestCase):
    def test_parses_legacy_array_response(self):
        response = json.dumps(
            [
                {
                    "title": "项目评审",
                    "date": "2026-07-20",
                    "start_time": "14:30",
                    "urgency": "important",
                }
            ],
            ensure_ascii=False,
        )

        items = parse_model_response(response)

        self.assertEqual(items[0]["title"], "项目评审")
        self.assertEqual(items[0]["urgency"], "important")

    @patch("core.workflow.call_model")
    def test_text_workflow_returns_normalized_schedule(self, call_model):
        call_model.return_value = json.dumps(
            {
                "schedules": [
                    {
                        "title": "提交报告",
                        "date": "2026-07-21",
                        "start_time": "09:00",
                        "repeat": "none",
                        "urgency": "urgent",
                    }
                ]
            },
            ensure_ascii=False,
        )

        schedules = process_input("text", "下周二早上九点提交报告")

        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["date"], datetime.date(2026, 7, 21))
        self.assertEqual(schedules[0]["start_time"], datetime.time(9, 0))
        self.assertEqual(schedules[0]["urgency"], 2)
        self.assertEqual(call_model.call_count, 1)

    def test_empty_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "输入内容不能为空"):
            process_input("text", "")

    @patch("core.workflow.call_model")
    def test_model_and_parser_share_one_date_context(self, call_model):
        call_model.return_value = json.dumps(
            {"schedules": [{"title": "复诊", "date": "明天"}]},
            ensure_ascii=False,
        )
        context = get_date_context(
            datetime.datetime(
                2026, 12, 31, 23, 59, tzinfo=datetime.timezone(datetime.timedelta(hours=8))
            )
        )

        schedules = process_input("text", "明天复诊", date_context=context)

        system_prompt = call_model.call_args.args[0][0]["content"]
        self.assertIn("2026-12-31 23:59:00", system_prompt)
        self.assertIn("UTC+08:00", system_prompt)
        self.assertEqual(schedules[0]["date"], datetime.date(2027, 1, 1))

    @patch("core.workflow.call_model")
    def test_image_workflow_combines_multiple_images(self, call_model):
        call_model.side_effect = [
            '{"schedules": [{"title": "会议 A", "urgency": "normal"}]}',
            '{"schedules": [{"title": "会议 B", "urgency": "important"}]}',
        ]
        paths = []
        try:
            for _ in range(2):
                image = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image.write(b"fake image bytes")
                image.close()
                paths.append(image.name)

            schedules = process_input("image", paths)

            self.assertEqual([item["title"] for item in schedules], ["会议 A", "会议 B"])
            self.assertEqual(call_model.call_count, 2)
            self.assertEqual(call_model.call_args_list[0].kwargs["task_type"], "image")
            first_messages = call_model.call_args_list[0].args[0]
            image_url = first_messages[1]["content"][1]["image_url"]["url"]
            self.assertTrue(image_url.startswith("data:image/png;base64,"))
        finally:
            for path in paths:
                os.unlink(path)

    @patch("core.workflow.call_model")
    def test_empty_text_result_is_retried_then_saved_as_undated_todo(self, call_model):
        call_model.side_effect = ['{"schedules": []}', '{"schedules": []}']

        schedules = process_input("text", "理发")

        self.assertEqual(call_model.call_count, 2)
        self.assertEqual(schedules[0]["title"], "理发")
        self.assertIsNone(schedules[0]["date"])

    @patch("core.workflow.time.sleep")
    @patch("core.workflow.call_model")
    def test_rate_limit_is_retried_without_immediate_failure(self, call_model, sleep):
        busy = RuntimeError("Error code: 429 - 访问量过大，请稍后再试")
        busy.status_code = 429
        call_model.side_effect = [busy, '{"schedules": [{"title": "交材料"}]}']
        progress = []

        schedules = process_input("text", "交材料", progress=progress.append)

        self.assertEqual(schedules[0]["title"], "交材料")
        sleep.assert_called_once_with(3)
        self.assertTrue(any("自动重试" in message for message in progress))


if __name__ == "__main__":
    unittest.main()
