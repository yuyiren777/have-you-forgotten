"""Server酱 (ServerChan) 推送"""
import httpx

SERVERCHAN_URL = 'https://sctapi.ftqq.com/{send_key}.send'


def send(send_key: str, title: str, content: str = '') -> tuple[bool, str]:
    """通过 Server酱 发送微信推送

    Args:
        send_key: Server酱 SendKey
        title: 推送标题
        content: 推送内容（支持 Markdown）

    Returns:
        (success, message)
    """
    if not send_key:
        return False, 'SendKey 未配置'

    try:
        resp = httpx.post(
            SERVERCHAN_URL.format(send_key=send_key),
            json={
                'title': title,
                'desp': content,
            },
            timeout=15.0
        )
        data = resp.json()
        if data.get('code') == 0:
            return True, '推送成功'
        return False, f"推送失败: {data.get('message', '未知错误')}"
    except httpx.RequestError as e:
        return False, f'网络错误: {e}'
    except Exception as e:
        return False, f'推送异常: {e}'
