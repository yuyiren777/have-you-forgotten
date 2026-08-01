"""Runtime checks for the required AI orchestration frameworks."""

import langchain
import langchain_core
import langgraph


def verify_ai_frameworks() -> None:
    """Fail early with a useful message when a packaged dependency is missing."""
    required = {
        "LangChain": langchain,
        "LangChain Core": langchain_core,
        "LangGraph": langgraph,
    }
    missing = [name for name, module in required.items() if module is None]
    if missing:
        raise RuntimeError(f"缺少必要的 AI 工作流组件: {', '.join(missing)}")
