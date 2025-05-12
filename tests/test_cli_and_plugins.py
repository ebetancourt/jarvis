import os
import sys
import subprocess
import importlib
import pytest

JARVIS_CLI = os.path.join(os.path.dirname(__file__), '..', 'jarvis.py')

@pytest.mark.skipif(not os.path.exists(JARVIS_CLI), reason="jarvis.py not found")
def test_jarvis_cli_runs():
    # Run the CLI with a dummy question and check for output (smoke test)
    result = subprocess.run([sys.executable, JARVIS_CLI, "What is this project?"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Answer:" in result.stdout

@pytest.mark.xfail(reason="plugins.obsidian not yet implemented")
def test_import_plugins_obsidian():
    importlib.import_module("plugins.obsidian")

@pytest.mark.xfail(reason="plugins.gmail not yet implemented")
def test_import_plugins_gmail():
    importlib.import_module("plugins.gmail")
