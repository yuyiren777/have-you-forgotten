"""深度求索 — DeepSeek-V3 (OpenAI 兼容接口，纯文本)"""
from openai import OpenAI

DEFAULT_BASE_URL = 'https://api.deepseek.com'
DEFAULT_MODEL = 'deepseek-chat'


def call(
    api_key: str,
    messages: list[dict],
    base_url: str = '',
    model: str = '',
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """调用 DeepSeek API（纯文本，不支持图片）"""
    # 过滤掉图片内容，只保留文本
    text_messages = []
    for msg in messages:
        content = msg.get('content', '')
        if isinstance(content, list):
            # 从多模态内容中提取纯文本
            text_parts = [p.get('text', '') for p in content if p.get('type') == 'text']
            text_content = ' '.join(text_parts)
        else:
            text_content = str(content)
        text_messages.append({'role': msg['role'], 'content': text_content})

    client = OpenAI(
        api_key=api_key,
        base_url=base_url or DEFAULT_BASE_URL,
    )
    response = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=text_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
