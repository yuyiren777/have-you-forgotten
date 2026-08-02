"""Human-readable schedule fields for notifications and cards."""

import json


def clean_optional_text(value) -> str:
    """Normalize database null-like values to an empty display value."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "undefined"}:
        return ""
    return text


def readable_notes(raw_notes) -> str:
    """Extract a user-facing note from legacy JSON or current plain text."""
    text = clean_optional_text(raw_notes)
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text

    if isinstance(parsed, dict):
        return clean_optional_text(parsed.get("notes") or parsed.get("description"))
    if isinstance(parsed, str):
        return clean_optional_text(parsed)
    return ""
