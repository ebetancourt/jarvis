import os
import stat
from pathlib import Path
from datetime import date
from typing import Optional
from common.data import DATA_DIR


def ensure_journal_directory() -> str:
    """
    Ensures the existence of the /src/data/journal/ directory structure with proper
    permissions.

    Creates the directory if it doesn't exist and sets appropriate permissions for
    read/write access.

    Returns:
        str: The absolute path to the journal directory

    Raises:
        OSError: If directory creation fails due to permissions or other filesystem
                 issues
        PermissionError: If unable to set proper permissions on the directory
    """
    # Define the journal directory path using DATA_DIR
    journal_dir = Path(os.path.join(DATA_DIR, "journal"))

    try:
        # Create directory if it doesn't exist (parents=True creates intermediates)
        journal_dir.mkdir(parents=True, exist_ok=True)

        # Set proper permissions (read/write for owner, read for group and others)
        # 0o755 = rwxr-xr-x (owner: read/write/execute, group/others: read/execute)
        os.chmod(
            journal_dir,
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
        )

        return str(journal_dir.absolute())

    except PermissionError as e:
        raise PermissionError(
            f"Unable to create or set permissions for journal directory: {e}"
        )
    except OSError as e:
        raise OSError(f"Failed to create journal directory: {e}")


def create_daily_file(target_date: Optional[date] = None) -> str:
    """
    Creates a daily journal file with the naming format YYYY-MM-DD.md.

    Creates the file if it doesn't exist. If it already exists, returns the path
    to the existing file.

    Args:
        target_date: The date for the journal file. If None, uses today's date.

    Returns:
        str: The absolute path to the created (or existing) daily journal file

    Raises:
        OSError: If file creation fails due to permissions or other filesystem issues
    """
    # Ensure the journal directory exists first
    journal_dir = ensure_journal_directory()

    # Use today's date if no date is provided
    if target_date is None:
        target_date = date.today()

    # Generate the filename in YYYY-MM-DD.md format
    filename = f"{target_date.strftime('%Y-%m-%d')}.md"
    file_path = os.path.join(journal_dir, filename)

    try:
        # Create the file if it doesn't exist (touch behavior)
        Path(file_path).touch(exist_ok=True)
        return file_path
    except OSError as e:
        raise OSError(f"Failed to create daily journal file {filename}: {e}")


def get_journal_directory() -> str:
    """
    Gets the absolute path to the journal directory.

    Returns:
        str: The absolute path to the journal directory
    """
    return os.path.join(DATA_DIR, "journal")
