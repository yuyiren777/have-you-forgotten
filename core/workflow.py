"""LangGraph workflow for extracting and normalizing schedule input."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from collections.abc import Callable
from typing import Literal, TypedDict

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from core.api_client import call_model
from core.parser import parse_schedule_list
from utils.date_context import DateContext, get_date_context


class ScheduleItem(BaseModel):
    """Validated representation returned by the language model."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1)
    description: str | None = None
    date: str | None = None
    date_year_explicit: bool | None = Field(
        default=None,
        description="True only when the original source explicitly contains a year.",
    )
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    repeat: str = "none"
    urgency: Literal["normal", "important", "urgent"] = "normal"


class ScheduleExtraction(BaseModel):
    schedules: list[ScheduleItem] = Field(default_factory=list)


class WorkflowState(TypedDict, total=False):
    source_type: Literal["text", "image"]
    source_data: str | list[str]
    provider: str
    progress: Callable[[str], None] | None
    date_context: DateContext
    raw_responses: list[str]
    image_data_urls: dict[str, str]
    items: list[dict]
    schedules: list[dict]


_output_parser = PydanticOutputParser(pydantic_object=ScheduleExtraction)

_SYSTEM_PROMPT = """你是一个日程提取助手。请从用户提供的内容中提取会议、约会、截止日期和活动。
结合上下文纠正明显的同音字或输入法错误，但不要随意修改人名和地名。
当前本地日期和时间是 {current_datetime}。请以此为唯一基准，把相对日期转换为 YYYY-MM-DD；无法确定的字段使用 null。
重复规则使用 none、daily、weekly:1（周一为 1）或 monthly:15。

{format_instructions}
日期规则：只有原文明确写出年份时，date_year_explicit 才能设为 true。
原文只有月日（例如“12月30日”）时必须设为 false，并选择从今天起最近一次尚未过去的该月日；
年底遇到较小月份时应跨到下一年。不得使用图片元数据、训练数据或自行猜测的年份。
只返回符合上述结构的 JSON，不要添加解释。"""

_text_prompt = ChatPromptTemplate.from_messages(
    [("system", _SYSTEM_PROMPT), ("human", "{content}")]
)

_EMPTY_RESULT_INSTRUCTION = """
这是用户主动提交、希望软件帮忙记住的内容。即使没有日期、时间，或者只写了“理发”一类简短事项，
也必须提取为至少一条待办；不确定的日期和时间填写 null。不要因为它不像传统会议日程而返回空数组。
"""

_RETRY_DELAYS = (3, 5, 8, 12, 15)


def _emit(state: WorkflowState, message: str) -> None:
    callback = state.get("progress")
    if callback:
        callback(message)


def _to_provider_messages(prompt_value) -> list[dict]:
    role_map = {"system": "system", "human": "user", "ai": "assistant"}
    return [
        {"role": role_map.get(message.type, message.type), "content": message.content}
        for message in prompt_value.to_messages()
    ]


def _is_retryable_model_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code in (409, 429):
        return True
    message = str(error).lower()
    markers = (
        "error code: 409",
        "error code: 429",
        "'code': '1305'",
        '"code":"1305"',
        "访问量过大",
        "稍后再试",
        "rate limit",
        "too many requests",
        "conflict",
    )
    return any(marker in message for marker in markers)


def _call_with_retry(
    messages: list[dict],
    state: WorkflowState,
    task_type: Literal["text", "image"],
) -> str:
    provider = state.get("provider", "")
    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            return call_model(messages, provider, task_type=task_type)
        except Exception as error:
            if not _is_retryable_model_error(error) or attempt >= len(_RETRY_DELAYS):
                if _is_retryable_model_error(error):
                    raise RuntimeError(
                        f"AI 服务持续繁忙，已自动重试 {attempt + 1} 次仍未成功，请稍后再试。"
                    ) from error
                raise
            delay = _RETRY_DELAYS[attempt]
            _emit(
                state,
                f"AI 服务繁忙，{delay} 秒后自动重试（{attempt + 1}/{len(_RETRY_DELAYS)}）...",
            )
            time.sleep(delay)


def _validate_input(state: WorkflowState) -> dict:
    source_type = state.get("source_type")
    source_data = state.get("source_data")
    if source_type not in ("text", "image"):
        raise ValueError("source_type 必须是 text 或 image")
    if not source_data:
        raise ValueError("输入内容不能为空")
    return {"date_context": state.get("date_context") or get_date_context()}


def _extract_text(state: WorkflowState) -> dict:
    _emit(state, "正在调用模型识别文字...")
    date_context = state["date_context"]
    prompt_value = _text_prompt.invoke(
        {
            "content": str(state["source_data"]),
            "current_datetime": date_context.to_prompt_text(),
            "format_instructions": _output_parser.get_format_instructions(),
        }
    )
    response = _call_with_retry(_to_provider_messages(prompt_value), state, "text")
    return {"raw_responses": [response]}


def _image_data_url(image_path: str) -> str:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"图片不存在: {image_path}")
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(os.path.splitext(image_path)[1].lower(), "image/png")
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _image_messages(
    state: WorkflowState,
    path: str,
    fallback: bool = False,
    data_url: str | None = None,
) -> list[dict]:
    date_context = state["date_context"]
    system_text = _SYSTEM_PROMPT.format(
        current_datetime=date_context.to_prompt_text(),
        format_instructions=_output_parser.get_format_instructions(),
    )
    instruction = "请提取这张图片中的全部日程信息。"
    if fallback:
        instruction += _EMPTY_RESULT_INSTRUCTION
    return [
        {"role": "system", "content": system_text},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": instruction},
                {"type": "image_url", "image_url": {"url": data_url or _image_data_url(path)}},
            ],
        },
    ]


def _extract_images(state: WorkflowState) -> dict:
    paths = state["source_data"]
    paths = paths if isinstance(paths, list) else [paths]
    responses = []
    image_data_urls = {}
    for index, path in enumerate(paths, start=1):
        _emit(state, f"正在识别图片 ({index}/{len(paths)})...")
        data_url = _image_data_url(path)
        image_data_urls[str(path)] = data_url
        responses.append(
            _call_with_retry(
                _image_messages(state, path, data_url=data_url), state, "image"
            )
        )
    return {"raw_responses": responses, "image_data_urls": image_data_urls}


def _legacy_json_items(response: str) -> list[dict]:
    """Accept older providers that ignore the requested wrapper object."""
    candidates = [response]
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if fenced:
        candidates.append(fenced.group(1))
    array = re.search(r"\[[\s\S]*\]", response)
    if array:
        candidates.append(array.group())

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            data = data.get("schedules", [data])
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    return []


def parse_model_response(response: str) -> list[dict]:
    """Parse and validate one model response with a compatibility fallback."""
    try:
        parsed = _output_parser.parse(response)
        return [item.model_dump() for item in parsed.schedules]
    except Exception as structured_error:
        items = _legacy_json_items(response)
        validated = []
        for item in items:
            try:
                validated.append(ScheduleItem.model_validate(item).model_dump())
            except Exception:
                continue
        if validated or (not items and response.strip() in ("[]", '{"schedules": []}')):
            return validated
        raise ValueError("模型没有返回有效的日程 JSON") from structured_error


def _parse_responses(state: WorkflowState) -> dict:
    _emit(state, "识别完成，正在校验结构...")
    items = []
    for response in state.get("raw_responses", []):
        try:
            items.extend(parse_model_response(response))
        except ValueError:
            continue

    if items:
        return {"items": items}

    _emit(state, "未识别到明确日程，正在进行兜底识别...")
    retry_responses = []
    if state["source_type"] == "text":
        date_context = state["date_context"]
        prompt_value = _text_prompt.invoke(
            {
                "content": f"{state['source_data']}\n\n{_EMPTY_RESULT_INSTRUCTION}",
                "current_datetime": date_context.to_prompt_text(),
                "format_instructions": _output_parser.get_format_instructions(),
            }
        )
        retry_responses.append(
            _call_with_retry(_to_provider_messages(prompt_value), state, "text")
        )
    else:
        paths = state["source_data"]
        paths = paths if isinstance(paths, list) else [paths]
        image_data_urls = state.get("image_data_urls", {})
        for path in paths:
            retry_responses.append(
                _call_with_retry(
                    _image_messages(
                        state,
                        path,
                        fallback=True,
                        data_url=image_data_urls.get(str(path)),
                    ),
                    state,
                    "image",
                )
            )

    for response in retry_responses:
        try:
            items.extend(parse_model_response(response))
        except ValueError:
            continue

    if not items:
        items = _build_local_fallback_items(state)
        _emit(state, "AI 未能提取结构，已保留为可编辑的无日期待办。")
    return {"items": items}


def _build_local_fallback_items(state: WorkflowState) -> list[dict]:
    """Never discard user-submitted content when the model returns no schedules."""
    if state["source_type"] == "text":
        content = " ".join(str(state["source_data"]).split()).strip()
        return [
            {
                "title": content[:120] or "未命名待办",
                "description": content or None,
                "date": None,
                "date_year_explicit": False,
                "start_time": None,
                "end_time": None,
                "location": None,
                "repeat": "none",
                "urgency": "normal",
            }
        ]

    paths = state["source_data"]
    paths = paths if isinstance(paths, list) else [paths]
    multiple = len(paths) > 1
    return [
        {
            "title": f"待整理的图片备忘（{index}）" if multiple else "待整理的图片备忘",
            "description": "AI 未能从图片中提取明确日程，请打开日程后补充内容。",
            "date": None,
            "date_year_explicit": False,
            "start_time": None,
            "end_time": None,
            "location": None,
            "repeat": "none",
            "urgency": "normal",
        }
        for index, _path in enumerate(paths, start=1)
    ]


def _normalize_schedules(state: WorkflowState) -> dict:
    schedules = parse_schedule_list(
        state.get("items", []), today=state["date_context"].today
    )
    _emit(state, f"已解析 {len(schedules)} 条日程")
    return {"schedules": schedules}


def _route_source(state: WorkflowState) -> str:
    return state["source_type"]


def _build_workflow():
    graph = StateGraph(WorkflowState)
    graph.add_node("validate_input", _validate_input)
    graph.add_node("extract_text", _extract_text)
    graph.add_node("extract_images", _extract_images)
    graph.add_node("parse_responses", _parse_responses)
    graph.add_node("normalize_schedules", _normalize_schedules)
    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        _route_source,
        {"text": "extract_text", "image": "extract_images"},
    )
    graph.add_edge("extract_text", "parse_responses")
    graph.add_edge("extract_images", "parse_responses")
    graph.add_edge("parse_responses", "normalize_schedules")
    graph.add_edge("normalize_schedules", END)
    return graph.compile()


schedule_workflow = _build_workflow()


def process_input(
    source_type: Literal["text", "image"],
    source_data: str | list[str],
    *,
    provider: str = "",
    progress: Callable[[str], None] | None = None,
    date_context: DateContext | None = None,
) -> list[dict]:
    """Run the complete extraction workflow and return DB-ready schedules."""
    result = schedule_workflow.invoke(
        {
            "source_type": source_type,
            "source_data": source_data,
            "provider": provider,
            "progress": progress,
            "date_context": date_context,
        }
    )
    return result["schedules"]


def extract_input(
    source_type: Literal["text", "image"], source_data: str | list[str]
) -> list[dict]:
    """Compatibility entry point returning validated, non-normalized items."""
    result = schedule_workflow.invoke(
        {"source_type": source_type, "source_data": source_data, "provider": ""}
    )
    return result["items"]
