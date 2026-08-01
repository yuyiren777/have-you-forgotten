import langchain
import langchain_core
import langgraph

from core.frameworks import verify_ai_frameworks
from core.workflow import schedule_workflow


def test_required_ai_frameworks_are_installed_and_workflow_is_compiled():
    verify_ai_frameworks()

    assert langchain is not None
    assert langchain_core is not None
    assert langgraph is not None
    assert schedule_workflow.__class__.__module__.startswith("langgraph.")
