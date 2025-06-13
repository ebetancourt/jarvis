import os
import stat
from pathlib import Path
from datetime import date, datetime, time
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


def format_file_title(target_date: Optional[date] = None) -> str:
    """
    Formats a date into a journal file title.

    Creates a title in the format:
    "# <DAY OF THE WEEK>, <CARDINAL DATE> of <MONTH> <YEAR>"
    For example: "# Friday, 13th of June 2025"

    Args:
        target_date: The date to format. If None, uses today's date.

    Returns:
        str: The formatted title string starting with "# "
    """
    # Use today's date if no date is provided
    if target_date is None:
        target_date = date.today()

    # Get day of the week (e.g., "Friday")
    day_of_week = target_date.strftime("%A")

    # Get month name (e.g., "June")
    month_name = target_date.strftime("%B")

    # Get year (e.g., "2025")
    year = target_date.strftime("%Y")

    # Get day and format with ordinal suffix (e.g., "13th")
    day = target_date.day
    if 10 <= day % 100 <= 20:  # Special case for 11th, 12th, 13th
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    cardinal_date = f"{day}{suffix}"

    # Format the complete title
    return f"# {day_of_week}, {cardinal_date} of {month_name} {year}"


def add_timestamp_entry(
    content: str, target_date: Optional[date] = None, target_time: Optional[time] = None
) -> str:
    """
    Adds a timestamped entry to a daily journal file.

    Creates the daily file if it doesn't exist, adds the file title if it's the first
    entry of the day, then adds a timestamp heading and the entry content.

    Args:
        content: The journal entry content to add
        target_date: The date for the journal entry. If None, uses today's date.
        target_time: The time for the timestamp. If None, uses current time.

    Returns:
        str: The absolute path to the journal file that was updated

    Raises:
        OSError: If file operations fail due to permissions or other filesystem issues
    """
    # Use today's date if no date is provided
    if target_date is None:
        target_date = date.today()

    # Use current time if no time is provided
    if target_time is None:
        target_time = datetime.now().time()

    # Get the daily file path
    file_path = create_daily_file(target_date)

    try:
        # Check if file is empty (new file needs title)
        file_size = os.path.getsize(file_path)
        is_new_file = file_size == 0

        # Build the new entry content
        entry_parts = []

        # Add title if this is a new file
        if is_new_file:
            title = format_file_title(target_date)
            entry_parts.append(title)
            entry_parts.append("")  # Empty line after title

        # Add timestamp heading
        timestamp = target_time.strftime("%H:%M:%S")
        entry_parts.append(f"## {timestamp}")
        entry_parts.append("")  # Empty line after timestamp

        # Add the entry content
        entry_parts.append(content)

        # Combine entry parts
        entry_content = "\n".join(entry_parts)

        # Use append function for consistent file handling
        if is_new_file:
            # For new files, write directly (no existing content to append to)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(entry_content)
        else:
            # For existing files, use the append utility
            append_to_existing_file(file_path, entry_content)

        return file_path

    except OSError as e:
        raise OSError(f"Failed to add timestamp entry to journal file: {e}")


def append_to_existing_file(file_path: str, content: str) -> None:
    """
    Appends content to an existing file with proper formatting.

    Reads the existing file content, adds appropriate spacing, and appends the new
    content. Handles empty files and ensures proper line separation between entries.

    Args:
        file_path: Absolute path to the file to append to
        content: The content to append to the file

    Raises:
        OSError: If file operations fail due to permissions or other filesystem issues
        FileNotFoundError: If the specified file doesn't exist
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Journal file does not exist: {file_path}")

        # Read existing content
        with open(file_path, "r", encoding="utf-8") as f:
            existing_content = f.read().strip()

        # Build the new content
        if existing_content:
            # File has content, add spacing before new content
            new_content = existing_content + "\n\n" + content
        else:
            # File is empty, just add the content
            new_content = content

        # Write the complete content back to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    except FileNotFoundError:
        raise
    except OSError as e:
        raise OSError(f"Failed to append to journal file {file_path}: {e}")


def get_journal_directory() -> str:
    """
    Gets the absolute path to the journal directory.

    Returns:
        str: The absolute path to the journal directory
    """
    return os.path.join(DATA_DIR, "journal")
