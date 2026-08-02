from unittest.mock import Mock, patch

from push.email_sender import build_schedule_email, send


@patch("push.email_sender.smtplib.SMTP_SSL")
def test_qq_sender_header_keeps_address_outside_encoded_display_name(smtp_ssl):
    server = Mock()
    smtp_ssl.return_value.__enter__.return_value = server

    ok, _ = send(
        service="qq",
        email_address="123456@qq.com",
        email_password="authorization-code",
        to_address="123456@qq.com",
        subject="test",
        html_content="<p>test</p>",
    )

    assert ok
    message = server.send_message.call_args.args[0]
    assert message["From"].endswith("<123456@qq.com>")
    assert "=?utf-8?" in message["From"]


def test_schedule_email_uses_plain_chinese_labels_and_escapes_values():
    html = build_schedule_email(
        title="复习 <数学>",
        date_str="2026-08-02 14:40",
        location="A&B",
        notes="记得带计算器",
        remaining="还有1小时",
    )

    assert "日程：复习 &lt;数学&gt;" in html
    assert "地点：</strong>A&amp;B" in html
    assert "备注：</strong>记得带计算器" in html
    assert not any(icon in html for icon in "⏰📌📅📍⏳📝")
