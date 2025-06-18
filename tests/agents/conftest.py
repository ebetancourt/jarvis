import os

import pytest


def _import_journaling_agent():
    """Import journaling agent module dynamically to avoid dependency issues."""
    import importlib.util

    # Get the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(current_dir, "..", "..", "src", "agents", "journaling_agent.py")
    module_path = os.path.normpath(module_path)

    spec = importlib.util.spec_from_file_location("journaling_agent", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def conversation_state():
    """Fixture for creating a fresh JournalingConversationState instance."""
    journaling_agent = _import_journaling_agent()
    return journaling_agent.JournalingConversationState()
