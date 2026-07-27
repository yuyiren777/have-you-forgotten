from unittest.mock import Mock, patch

from push.email_sender import send


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
