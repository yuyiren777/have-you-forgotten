"""多模型 API 统一调用入口"""
import base64
import os
from typing import Optional
from db.database import get_db
from db.models import Config
from utils.crypto import decrypt


PROVIDERS = {
    'zhipu': 'core.providers.zhipu',
    'qwen': 'core.providers.qwen',
    'deepseek': 'core.providers.deepseek',
    'ernie': 'core.providers.ernie',
    'custom': 'core.providers.custom',
}

PROVIDER_NAMES = {
    'zhipu': '智谱 GLM-4V',
    'qwen': '通义千问 Qwen-VL-Max',
    'deepseek': 'DeepSeek-V3',
    'ernie': '文心一言 ERNIE-4.0',
    'custom': '自定义 API',
}


def _get_config(key: str, default: str = '') -> str:
    """从数据库获取配置"""
    try:
        db = get_db()
        row = Config.get_or_none(Config.key == key)
        if row:
            val = row.value
            # 敏感字段解密
            if key in ('model_api_key', 'wechat_token', 'email_address', 'email_password'):
                val = decrypt(val)
            return val
    except Exception:
        pass
    return default


def get_provider_config() -> dict:
    """获取当前模型配置"""
    return {
        'provider': _get_config('model_provider', 'zhipu'),
        'api_key': _get_config('model_api_key', ''),
        'api_base': _get_config('model_api_base', ''),
        'model': _get_config('model_name', ''),
    }


def get_push_config() -> dict:
    """获取推送配置"""
    return {
        'wechat_service': _get_config('wechat_service', 'none'),
        'wechat_token': _get_config('wechat_token', ''),
        'email_service': _get_config('email_service', 'none'),
        'email_address': _get_config('email_address', ''),
        'email_password': _get_config('email_password', ''),
        'email_smtp_host': _get_config('email_smtp_host', ''),
        'email_smtp_port': _get_config('email_smtp_port', ''),
    }


def get_model_name() -> str:
    """获取当前使用的模型名称（用于显示）"""
    provider = _get_config('model_provider', 'zhipu')
    return PROVIDER_NAMES.get(provider, provider)


def is_setup_complete() -> bool:
    """Return whether the user finished onboarding with a usable model key."""
    completed = _get_config('setup_completed', '0') == '1'
    return completed and bool(_get_config('model_api_key', '').strip())


def call_model(messages: list[dict], provider: str = '') -> str:
    """统一调用大模型

    Args:
        messages: 消息列表，支持多模态（图片用 base64）
        provider: 指定 provider，为空则从配置读取

    Returns:
        模型回复文本
    """
    config = get_provider_config()
    if provider:
        config['provider'] = provider

    p = config['provider']
    if p not in PROVIDERS:
        raise ValueError(f'不支持的模型提供商: {p}。可选: {", ".join(PROVIDERS.keys())}')

    module = __import__(PROVIDERS[p], fromlist=['call'])
    return module.call(
        api_key=config['api_key'],
        messages=messages,
        base_url=config['api_base'],
        model=config['model'],
    )


def call_ocr(image_path: str, provider: str = '') -> str:
    """调用视觉模型识别图片中的文字和日程

    Args:
        image_path: 图片文件路径
        provider: 指定 provider

    Returns:
        模型回复文本（JSON 格式的日程列表）
    """
    # 读取图片并转 base64
    with open(image_path, 'rb') as f:
        img_data = base64.b64encode(f.read()).decode('utf-8')

    # 判断图片类型
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp'}
    mime_type = mime_map.get(ext, 'image/png')

    # 系统提示
    system_prompt = """你是一个日程提取助手。请仔细查看图片中的所有文字，提取其中包含的日程、会议、约会、截止日期、活动等信息。

重要：用户可能使用了错别字、同音字或拼音输入法导致的错误（如"灶上"→"早上"、"电"→"点"、"昨田"→"昨天"、"下周无"→"下周五"等）。请你根据上下文自动纠正这些错误，提取正确的日程信息。

对于每条日程，请以严格 JSON 数组格式输出：

[
  {
    "title": "日程标题",
    "description": "详细描述",
    "date": "YYYY-MM-DD 或 null",
    "start_time": "HH:MM 或 null",
    "end_time": "HH:MM 或 null",
    "location": "地点 或 null",
    "repeat": "none 或 daily 或 weekly:周几 或 monthly:几号",
    "urgency": "normal 或 important 或 urgent"
  }
]

日期理解规则：
- "明天" = 明天日期，写成绝对日期格式
- "今天" = 今天日期
- "后天" = 后天日期
- "下周三" = 下一个周三的日期
- "每周一" = repeat 填 "weekly:1"（周一=1, 周二=2...周日=7）
- "每月15号" = repeat 填 "monthly:15"
- 如果只提到时间没提到日期，date 填 null
- 如果完全没提到时间，start_time 填 null
- 如果无法确定，填 null 即可

请只返回 JSON 数组，不要包含其他内容。"""

    messages = [
        {'role': 'system', 'content': system_prompt},
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': '请提取这张图片中的日程信息。'},
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:{mime_type};base64,{img_data}'
                    }
                },
            ],
        },
    ]

    return call_model(messages, provider)


def call_text_extract(text: str, provider: str = '') -> str:
    """从纯文本中提取日程

    Args:
        text: 用户输入的文字
        provider: 指定 provider

    Returns:
        模型回复文本（JSON 格式的日程列表）
    """
    system_prompt = """你是一个日程提取助手。请从以下文字中提取所有日程信息。

重要：用户输入可能包含错别字、同音字或拼音输入法导致的错误（如"灶上"→"早上"、"电"→"点"、"昨田"→"昨天"、"下周无"→"下周五"、"赴约"→"预约"等）。请你根据上下文自动纠正这些拼写错误，再从中提取日程。但对于正常的人名、地名不要随意修改。

对于每条日程，以严格 JSON 数组格式输出：

[
  {
    "title": "日程标题",
    "description": "详细描述",
    "date": "YYYY-MM-DD 或 null",
    "start_time": "HH:MM 或 null",
    "end_time": "HH:MM 或 null",
    "location": "地点 或 null",
    "repeat": "none 或 daily 或 weekly:周几 或 monthly:几号",
    "urgency": "normal 或 important 或 urgent"
  }
]

日期理解规则同前。请只返回 JSON 数组，不要包含其他内容。"""

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': text},
    ]

    # 纯文本优先用 DeepSeek（便宜）
    if not provider:
        config = get_provider_config()
        if config['provider'] in ('zhipu', 'qwen', 'ernie'):
            # 这些也支持文字，但 DeepSeek 更便宜
            # 如果用户没配 DeepSeek，会回退到当前 provider
            pass

    return call_model(messages, provider)


def test_connection(provider: str = '') -> tuple[bool, str]:
    """测试模型连接"""
    try:
        messages = [{'role': 'user', 'content': '你好，请回复"连接成功"。'}]
        result = call_model(messages, provider)
        if '连接成功' in result:
            return True, '连接成功'
        return True, f'连接正常（返回: {result[:50]}...）'
    except Exception as e:
        return False, f'连接失败: {e}'
