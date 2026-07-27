"""邮件推送（smtplib 标准库实现）"""
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, parseaddr

# 预置邮箱配置
EMAIL_CONFIG = {
    'qq': {
        'smtp_host': 'smtp.qq.com',
        'smtp_port': 465,
        'use_ssl': True,
        'name': 'QQ邮箱',
    },
    '163': {
        'smtp_host': 'smtp.163.com',
        'smtp_port': 465,
        'use_ssl': True,
        'name': '163邮箱',
    },
    'gmail': {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_ssl': False,
        'name': 'Gmail',
    },
}


def send(
    service: str,
    email_address: str,
    email_password: str,
    to_address: str,
    subject: str,
    html_content: str,
    custom_host: str = '',
    custom_port: int = 0,
) -> tuple[bool, str]:
    """发送邮件

    Args:
        service: 邮箱类型 ('qq' | '163' | 'gmail' | 'custom')
        email_address: 发件邮箱地址
        email_password: 授权码（不是邮箱密码）
        to_address: 收件邮箱地址
        subject: 邮件主题
        html_content: 邮件正文（HTML 格式）
        custom_host: 自定义 SMTP 服务器（service='custom' 时使用）
        custom_port: 自定义 SMTP 端口（service='custom' 时使用）

    Returns:
        (success, message)
    """
    if not email_address or not email_password:
        return False, '邮箱配置不完整'

    # QQ SMTP rejects an address wrapped inside an encoded-word.  Keep the
    # address ASCII and encode only the display name below.
    sender_name, sender_address = parseaddr(email_address.strip())
    if not sender_address or '@' not in sender_address:
        return False, '发件邮箱地址格式无效，请填写完整邮箱地址'

    # 获取 SMTP 配置
    if service in EMAIL_CONFIG:
        cfg = EMAIL_CONFIG[service]
        host = cfg['smtp_host']
        port = cfg['smtp_port']
        use_ssl = cfg['use_ssl']
    elif service == 'custom':
        if not custom_host or not custom_port:
            return False, '自定义 SMTP 配置不完整'
        host = custom_host
        port = custom_port
        use_ssl = port == 465
    else:
        return False, f'不支持的邮箱类型: {service}'

    # 构建邮件
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr((str(Header('智能日程助手', 'utf-8')), sender_address))
    msg['To'] = to_address or sender_address  # 默认发给自己

    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(sender_address, email_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                server.login(sender_address, email_password)
                server.send_message(msg)
        return True, '邮件发送成功'
    except smtplib.SMTPAuthenticationError:
        return False, '邮箱认证失败，请检查邮箱地址和授权码'
    except smtplib.SMTPException as e:
        return False, f'SMTP 错误: {e}'
    except Exception as e:
        return False, f'发送异常: {e}'


def build_schedule_email(title: str, date_str: str, location: str = '',
                         notes: str = '', remaining: str = '') -> str:
    """构建日程提醒 HTML 邮件"""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Microsoft YaHei', sans-serif; max-width: 500px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
        <h2 style="color: #fff; margin: 0;">⏰ 日程提醒</h2>
    </div>
    <div style="background: #fff; padding: 24px; border: 1px solid #e0e0e0;
                border-top: none; border-radius: 0 0 12px 12px;">
        <h3 style="color: #333; margin-top: 0;">📌 {title}</h3>
        <p style="color: #666; line-height: 1.8;">
            <strong>📅 时间：</strong>{date_str}<br>
            {f'<strong>📍 地点：</strong>{location}<br>' if location else ''}
            {f'<strong>⏳ 状态：</strong>{remaining}<br>' if remaining else ''}
            {f'<strong>📝 备注：</strong>{notes}<br>' if notes else ''}
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 16px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            —— 智能日程提醒助手
        </p>
    </div>
</body>
</html>"""
