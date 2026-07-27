"""WxPusher 推送"""
import httpx

WXPUSHER_URL = 'https://wxpusher.zjiecode.com/api/send/message'


def send(app_token: str, uid: str, title: str, content: str = '') -> tuple[bool, str]:
    """通过 WxPusher 发送微信推送

    Args:
        app_token: 应用 Token
        uid: 用户 UID
        title: 推送标题
        content: 推送内容

    Returns:
        (success, message)
    """
    if not app_token or not uid:
        return False, 'WxPusher 配置不完整'

    try:
        resp = httpx.post(
            WXPUSHER_URL,
            json={
                'appToken': app_token,
                'content': f'{title}\n\n{content}',
                'uid': uid,
                'contentType': 1,  # 文本
            },
            timeout=15.0
        )
        data = resp.json()
        if data.get('code') == 1000:
            return True, '推送成功'
        return False, f"推送失败: {data.get('msg', '未知错误')}"
    except httpx.RequestError as e:
        return False, f'网络错误: {e}'
    except Exception as e:
        return False, f'推送异常: {e}'
