"""多模型 API 统一调用入口"""
import base64
import os
from typing import Optional
from db.database import get_db
from db.models import Config
from utils.crypto import decrypt


PROVIDER_NAMES = {
    'zhipu': '文字 GLM-4.7-Flash · 图片 GLM-4.6V-Flash',
}

TEXT_MODEL = 'glm-4.7-flash'
VISION_MODEL = 'glm-4.6v-flash'


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
    provider = _get_config('model_provider', 'zhipu')
    if provider != 'zhipu':
        provider = 'zhipu'
    legacy_model = _get_config('model_name', '')
    mode = _get_config('model_mode', '')
    if mode not in ('unified', 'separate'):
        mode = 'unified' if legacy_model else 'separate'
    return {
        'provider': provider,
        'api_key': _get_config('model_api_key', ''),
        'api_base': _get_config('model_api_base', ''),
        'model_mode': mode,
        'unified_model': _get_config('unified_model_name', '') or legacy_model,
        'text_model': _get_config('text_model_name', ''),
        'image_model': _get_config('image_model_name', ''),
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
    config = get_provider_config()
    if config['model_mode'] == 'unified':
        return f"统一模型 {config['unified_model'] or VISION_MODEL}"
    return (
        f"文字 {config['text_model'] or TEXT_MODEL} · "
        f"图片 {config['image_model'] or VISION_MODEL}"
    )


def is_setup_complete() -> bool:
    """Return whether the user finished onboarding with a usable model key."""
    completed = _get_config('setup_completed', '0') == '1'
    return completed and bool(_get_config('model_api_key', '').strip())


def call_model(
    messages: list[dict], provider: str = '', task_type: str = 'text'
) -> str:
    """统一调用大模型

    Args:
        messages: 消息列表，支持多模态（图片用 base64）
        provider: 指定 provider，为空则从配置读取
        task_type: text 使用文字模型，image 使用视觉模型

    Returns:
        模型回复文本
    """
    config = get_provider_config()
    if provider:
        config['provider'] = provider

    if provider and provider != 'zhipu':
        raise ValueError('当前版本仅支持智谱 AI 模型服务。')

    if config.get('model_mode') == 'unified':
        model = config.get('unified_model') or VISION_MODEL
    elif task_type == 'image':
        model = config.get('image_model') or VISION_MODEL
    else:
        model = config.get('text_model') or TEXT_MODEL

    from core.providers.zhipu import call
    return call(
        api_key=config['api_key'],
        messages=messages,
        base_url=config['api_base'],
        model=model,
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

    return call_model(messages, provider, task_type='image')


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

    return call_model(messages, provider, task_type='text')


def test_connection(provider: str = '') -> tuple[bool, str]:
    """Test the selected model layout, including an actual image input."""
    try:
        config = get_provider_config()
        if config['model_mode'] == 'separate':
            call_model(
                [{'role': 'user', 'content': '请简短回复：文字模型连接成功。'}],
                provider,
                task_type='text',
            )

        pixel_png = (
            'data:image/png;base64,'
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
        )
        call_model(
            [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': '请简短回复：图片模型连接成功。'},
                        {'type': 'image_url', 'image_url': {'url': pixel_png}},
                    ],
                }
            ],
            provider,
            task_type='image',
        )
        if config['model_mode'] == 'unified':
            return True, '统一多模态模型连接成功，可处理文字和图片。'
        return True, '文字模型和图片模型均连接成功。'
    except Exception as e:
        return False, f'连接失败: {e}'
