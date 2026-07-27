"""PushPlus 推送"""
import httpx

PUSHPLUS_URL = 'https://www.pushplus.plus/send'


def send(token: str, title: str, content: str = '', template: str = 'html') -> tuple[bool, str]:
    """通过 PushPlus 发送微信推送

    Args:
        token: PushPlus Token
        title: 推送标题
        content: 推送内容
        template: 消息模板 (html | txt | json | markdown)

    Returns:
        (success, message)
    """
    if not token:
        return False, 'Token 未配置'

    try:
        resp = httpx.post(
            PUSHPLUS_URL,
            json={
                'token': token,
                'title': title,
                'content': content,
                'template': template,
            },
            timeout=15.0
        )
        data = resp.json()
        if data.get('code') == 200:
            return True, '推送成功'
        return False, f"推送失败: {data.get('msg', '未知错误')}"
    except httpx.RequestError as e:
        return False, f'网络错误: {e}'
    except Exception as e:
        return False, f'推送异常: {e}'
