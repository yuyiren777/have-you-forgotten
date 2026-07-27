"""Backward-compatible extraction API backed by the LangGraph workflow."""

from core.workflow import extract_input, parse_model_response


def extract_json_from_response(response: str) -> list[dict]:
    """Parse one response with LangChain/Pydantic validation."""
    return parse_model_response(response)


def process_image(image_path: str) -> list[dict]:
    """Extract validated schedule items from one image."""
    return extract_input("image", image_path)


def process_text(text: str) -> list[dict]:
    """Extract validated schedule items from text."""
    return extract_input("text", text)
