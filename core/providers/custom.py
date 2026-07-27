"""自定义 OpenAI 兼容接口（兜底方案）"""
from openai import OpenAI


def call(
    api_key: str,
    messages: list[dict],
    base_url: str = '',
    model: str = '',
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """调用任意 OpenAI 兼容 API"""
    if not base_url:
        raise ValueError('自定义模型需要提供 API 地址')

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    response = client.chat.completions.create(
        model=model or 'gpt-4o',
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
