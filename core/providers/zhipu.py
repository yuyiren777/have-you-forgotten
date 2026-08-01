"""智谱 AI OpenAI-compatible provider."""
from functools import lru_cache

from openai import OpenAI

DEFAULT_BASE_URL = 'https://open.bigmodel.cn/api/paas/v4/'
DEFAULT_MODEL = 'glm-4.7-flash'


@lru_cache(maxsize=4)
def _get_client(api_key: str, base_url: str) -> OpenAI:
    """Reuse HTTP connection pools between model calls."""
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=30.0,
    )


def call(
    api_key: str,
    messages: list[dict],
    base_url: str = '',
    model: str = '',
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """调用智谱 API

    Args:
        api_key: API Key
        messages: 消息列表，支持图片（base64 或 URL）
        base_url: API 地址
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大输出 token

    Returns:
        模型回复文本
    """
    client = _get_client(api_key, base_url or DEFAULT_BASE_URL)
    response = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
