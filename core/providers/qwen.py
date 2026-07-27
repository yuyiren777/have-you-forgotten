"""阿里通义千问 — Qwen-VL-Max (OpenAI 兼容接口)"""
from openai import OpenAI

DEFAULT_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
DEFAULT_MODEL = 'qwen-vl-max'


def call(
    api_key: str,
    messages: list[dict],
    base_url: str = '',
    model: str = '',
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """调用通义千问 API"""
    client = OpenAI(
        api_key=api_key,
        base_url=base_url or DEFAULT_BASE_URL,
    )
    response = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
