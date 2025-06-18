import os
import subprocess


def ensure_git_repo(path: str, repo_url: str, branch: str | None = None, token: str | None = None):
    """
    Ensure a git repository exists at the given path. If not, clone it. If it exists, pull the latest changes.
    Supports private GitHub repos via SSH or HTTPS with a token.

    Args:
        path (str): Local directory path where the repo should be.
        repo_url (str): Git repository URL (SSH or HTTPS).
        branch (Optional[str]): Branch to checkout/pull (default: default branch).
        token (Optional[str]): Personal access token for HTTPS URLs (if needed).
    """
    if os.path.isdir(os.path.join(path, ".git")):
        # Repo exists, pull latest
        try:
            print(f"Pulling latest changes in {path}...")
            subprocess.run(["git", "-C", path, "pull"], check=True)
            if branch:
                subprocess.run(["git", "-C", path, "checkout", branch], check=True)
                subprocess.run(["git", "-C", path, "pull", "origin", branch], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error pulling repo: {e}")
    else:
        # Repo does not exist, clone it
        try:
            print(f"Cloning repo {repo_url} into {path}...")
            clone_url = repo_url
            if token and repo_url.startswith("https://"):
                # Insert token into HTTPS URL
                clone_url = repo_url.replace("https://", f"https://{token}@")
            clone_cmd = ["git", "clone", clone_url, path]
            if branch:
                clone_cmd += ["-b", branch]
            subprocess.run(clone_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repo: {e}")
