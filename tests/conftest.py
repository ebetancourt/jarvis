import os
from unittest.mock import patch
import tempfile

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-docker", action="store_true", default=False, help="run docker integration tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: mark test as requiring docker containers")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-docker"):
        skip_docker = pytest.mark.skip(reason="need --run-docker option to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)


@pytest.fixture
def mock_env():
    """Fixture to ensure environment is clean for each test."""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def temp_weekly_reviews_json(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "weekly_reviews.json")
        monkeypatch.setenv("DATABASE_TYPE", "JSON")
        yield json_path
