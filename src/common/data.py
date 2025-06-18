import os
from utils.git_repo_manager import ensure_git_repo
from common.load_settings import load_settings

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
settings = load_settings()
GITHUB_TOKEN = settings["github_token"]


def refresh_data(repo_url: str, directory: str):
    """
    Ensure the given git repo is present and up-to-date.
    Args:
        repo_url (str): The git repository URL.
        directory (str): The subdirectory name under DATA_DIR.
    """
    path = os.path.join(DATA_DIR, directory)
    ensure_git_repo(path, repo_url, token=GITHUB_TOKEN)
