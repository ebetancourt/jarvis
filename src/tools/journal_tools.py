import os
import stat
import errno
import shutil
from pathlib import Path
from datetime import date, datetime, time
from typing import Optional
from common.data import DATA_DIR


def check_disk_space(path: str, required_bytes: int = 1024 * 1024) -> bool:
    """
    Checks if there's enough disk space available at the given path.

    Args:
        path: Path to check disk space for
        required_bytes: Minimum required bytes (default: 1MB)

    Returns:
        bool: True if enough space is available, False otherwise
    """
    try:
        _, _, free_bytes = shutil.disk_usage(path)
        return free_bytes >= required_bytes
    except OSError:
        # If we can't check disk space, assume it's available
        return True


def check_directory_permissions(directory: str) -> tuple[bool, bool, bool]:
    """
    Checks read, write, and execute permissions for a directory.

    Args:
        directory: Path to the directory to check

    Returns:
        tuple[bool, bool, bool]: (readable, writable, executable) permissions
    """
    try:
        readable = os.access(directory, os.R_OK)
        writable = os.access(directory, os.W_OK)
        executable = os.access(directory, os.X_OK)
        return readable, writable, executable
    except OSError:
        return False, False, False


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
        # Check if parent directory has enough disk space
        parent_dir = journal_dir.parent
        if not check_disk_space(str(parent_dir)):
            raise OSError(
                f"Insufficient disk space to create journal directory at {journal_dir}"
            )

        # Check parent directory permissions before attempting to create subdirectory
        if parent_dir.exists():
            readable, writable, executable = check_directory_permissions(
                str(parent_dir)
            )
            if not writable:
                raise PermissionError(
                    f"No write permission for parent directory {parent_dir}"
                )

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
        # Enhanced permission error handling
        if "parent directory" in str(e):
            raise e  # Re-raise our custom permission error
        else:
            raise PermissionError(
                f"Unable to create or set permissions for journal directory "
                f"{journal_dir}: {e}"
            )
    except OSError as e:
        # Enhanced OSError handling with specific error codes
        if e.errno == errno.ENOSPC:
            raise OSError(
                f"No space left on device to create journal directory {journal_dir}"
            )
        elif e.errno == errno.EACCES:
            raise PermissionError(
                f"Access denied when creating journal directory {journal_dir}"
            )
        elif e.errno == errno.EROFS:
            raise OSError(
                f"Read-only file system, cannot create journal directory {journal_dir}"
            )
        elif "Insufficient disk space" in str(e):
            raise e  # Re-raise our custom disk space error
        else:
            raise OSError(f"Failed to create journal directory {journal_dir}: {e}")


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
        # Check disk space before creating file
        if not check_disk_space(journal_dir):
            raise OSError(f"Insufficient disk space to create journal file {filename}")

        # Check directory permissions
        readable, writable, executable = check_directory_permissions(journal_dir)
        if not writable:
            raise PermissionError(
                f"No write permission for journal directory {journal_dir}"
            )

        # Create the file if it doesn't exist (touch behavior)
        Path(file_path).touch(exist_ok=True)
        return file_path
    except PermissionError:
        raise  # Re-raise permission errors as-is
    except OSError as e:
        # Enhanced OSError handling
        if e.errno == errno.ENOSPC:
            raise OSError(f"No space left on device to create file {filename}")
        elif e.errno == errno.EACCES:
            raise PermissionError(f"Access denied when creating file {filename}")
        elif e.errno == errno.EROFS:
            raise OSError(f"Read-only file system, cannot create file {filename}")
        elif "Insufficient disk space" in str(e):
            raise e  # Re-raise our custom disk space error
        else:
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
        try:
            file_size = os.path.getsize(file_path)
            is_new_file = file_size == 0
        except OSError as e:
            if e.errno == errno.EACCES:
                raise PermissionError(f"Access denied when accessing file {file_path}")
            else:
                raise OSError(f"Cannot access file {file_path}: {e}")

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
            # For new files, check permissions and disk space first
            file_dir = os.path.dirname(file_path)
            if not check_disk_space(file_dir, len(entry_content)):
                raise OSError("Insufficient disk space to write journal entry")

            # Write directly (no existing content to append to)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(entry_content)
        else:
            # For existing files, use the append utility (it has its own checks)
            append_to_existing_file(file_path, entry_content)

        return file_path

    except (PermissionError, FileNotFoundError):
        raise  # Re-raise these specific errors as-is
    except OSError as e:
        # Enhanced OSError handling
        if e.errno == errno.ENOSPC:
            raise OSError("No space left on device to add journal entry")
        elif e.errno == errno.EACCES:
            raise PermissionError("Access denied when writing journal entry")
        elif e.errno == errno.EROFS:
            raise OSError("Read-only file system, cannot write journal entry")
        elif "Insufficient disk space" in str(e):
            raise e  # Re-raise our custom disk space error
        else:
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

        # Check file permissions
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"No read permission for file {file_path}")
        if not os.access(file_path, os.W_OK):
            raise PermissionError(f"No write permission for file {file_path}")

        # Check disk space before writing
        file_dir = os.path.dirname(file_path)
        estimated_size = len(content) * 2  # Rough estimate with existing content
        if not check_disk_space(file_dir, estimated_size):
            raise OSError(f"Insufficient disk space to append to file {file_path}")

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

    except (FileNotFoundError, PermissionError):
        raise  # Re-raise these specific errors as-is
    except OSError as e:
        # Enhanced OSError handling
        if e.errno == errno.ENOSPC:
            raise OSError(f"No space left on device to append to file {file_path}")
        elif e.errno == errno.EACCES:
            raise PermissionError(f"Access denied when writing to file {file_path}")
        elif e.errno == errno.EROFS:
            raise OSError(f"Read-only file system, cannot write to file {file_path}")
        elif "Insufficient disk space" in str(e):
            raise e  # Re-raise our custom disk space error
        else:
            raise OSError(f"Failed to append to journal file {file_path}: {e}")


def get_journal_directory() -> str:
    """
    Gets the absolute path to the journal directory.

    Returns:
        str: The absolute path to the journal directory
    """
    return os.path.join(DATA_DIR, "journal")


def count_words(text: str) -> int:
    """
    Counts the number of words in a text string.

    Words are defined as sequences of non-whitespace characters separated by
    whitespace. This function handles multiple consecutive spaces, tabs, and
    newlines correctly.

    Args:
        text: The text string to count words in

    Returns:
        int: The number of words in the text
    """
    if not text or not text.strip():
        return 0

    # Split on whitespace and filter out empty strings
    words = text.split()
    return len(words)


def exceeds_word_limit(text: str, word_limit: int = 150) -> bool:
    """
    Checks if a text entry exceeds the specified word limit.

    This function is primarily used to determine if a journal entry should
    be summarized based on its length.

    Args:
        text: The text string to check
        word_limit: The maximum number of words allowed (default: 150)

    Returns:
        bool: True if the text exceeds the word limit, False otherwise
    """
    word_count = count_words(text)
    return word_count > word_limit


def generate_summary(text: str, max_summary_ratio: float = 0.2) -> str:
    """
    Generates an AI-powered summary of a journal entry.

    Uses the default LLM model to create a concise summary that captures the
    key themes, emotions, and insights from the original text. The summary
    is designed to be significantly shorter than the original while preserving
    the essential meaning and tone.

    Args:
        text: The journal entry text to summarize
        max_summary_ratio: Maximum ratio of summary length to original text (default: 0.2)

    Returns:
        str: A concise summary of the journal entry

    Raises:
        ValueError: If the text is empty or too short to meaningfully summarize
        OSError: If the AI model is unavailable or API calls fail
    """
    from langchain_core.messages import HumanMessage
    from core.llm import get_model
    from core.settings import settings

    # Validate input
    if not text or not text.strip():
        raise ValueError("Cannot summarize empty text")

    word_count = count_words(text)
    if word_count < 20:
        raise ValueError(
            "Text is too short to meaningfully summarize (minimum 20 words)"
        )

    # Calculate target summary length
    max_summary_words = max(10, int(word_count * max_summary_ratio))

    # Create the summarization prompt
    prompt = f"""You are helping to summarize a personal journal entry. Create a concise summary that:

1. Captures the main themes, emotions, and key events
2. Preserves the personal tone and important insights
3. Is no more than {max_summary_words} words
4. Focuses on what matters most to the writer

Journal Entry:
{text}

Please provide a thoughtful summary that the writer would find valuable for future reflection."""

    try:
        # Get the default model and create the message
        model = get_model(settings.DEFAULT_MODEL)

        # Disable streaming for synchronous summary generation
        model.streaming = False

        # Generate the summary
        response = model.invoke([HumanMessage(content=prompt)])

        summary = response.content.strip()

        # Validate the summary isn't empty
        if not summary:
            raise OSError("AI model returned empty summary")

        return summary

    except Exception as e:
        # Re-raise with more context
        if "API" in str(e) or "model" in str(e).lower():
            raise OSError(f"Failed to generate summary due to AI model error: {e}")
        else:
            raise OSError(f"Unexpected error during summary generation: {e}")
