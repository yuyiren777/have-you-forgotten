"""百度文心一言 — ERNIE-4.0 (独立 API 格式)"""
import httpx
import json

DEFAULT_BASE_URL = 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat'
DEFAULT_MODEL = 'completions_pro'

# 需要先通过 API Key + Secret Key 获取 access_token
_AUTH_URL = 'https://aip.baidubce.com/oauth/2.0/token'


def _get_access_token(api_key: str, secret_key: str) -> str:
    """用 API Key + Secret Key 获取 access_token"""
    resp = httpx.post(
        _AUTH_URL,
        params={
            'grant_type': 'client_credentials',
            'client_id': api_key,
            'client_secret': secret_key,
        },
        timeout=15.0
    )
    data = resp.json()
    return data.get('access_token', '')


def call(
    api_key: str,
    messages: list[dict],
    base_url: str = '',
    model: str = '',
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """调用文心一言 API"""
    # api_key 格式: "API_KEY:SECRET_KEY"
    if ':' in api_key:
        ak, sk = api_key.split(':', 1)
        access_token = _get_access_token(ak, sk)
    else:
        # 如果直接给的是 access_token
        access_token = api_key

    url = f'{base_url or DEFAULT_BASE_URL}/{model or DEFAULT_MODEL}'
    url += f'?access_token={access_token}'

    # 转换消息格式
    system_prompt = ''
    user_messages = []
    for msg in messages:
        role = msg['role']
        content = msg.get('content', '')
        if role == 'system':
            system_prompt = content if isinstance(content, str) else ''
        elif role == 'user':
            if isinstance(content, list):
                text_parts = [p.get('text', '') for p in content if p.get('type') == 'text']
                user_messages.append({'role': 'user', 'content': ' '.join(text_parts)})
            else:
                user_messages.append({'role': 'user', 'content': str(content)})

    body = {
        'messages': user_messages,
        'temperature': temperature,
        'max_output_tokens': max_tokens,
    }
    if system_prompt:
        body['system'] = system_prompt

    resp = httpx.post(url, json=body, timeout=60.0)
    data = resp.json()
    return data.get('result', '')
