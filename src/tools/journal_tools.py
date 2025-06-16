import os
import stat
import errno
import shutil
from pathlib import Path
from datetime import date, datetime, time
from typing import Optional, Dict, Any, List, Union
from common.data import DATA_DIR
from core.settings import settings
import yaml


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


def exceeds_word_limit(text: str, word_limit: Optional[int] = None) -> bool:
    """
    Check if the text exceeds the specified word limit.

    Uses configurable word count threshold from settings if no limit is provided.

    Args:
        text: The text to check
        word_limit: Optional custom word limit. If None, uses settings.JOURNALING_WORD_COUNT_THRESHOLD

    Returns:
        bool: True if the text exceeds the word limit, False otherwise
    """
    if word_limit is None:
        word_limit = settings.JOURNALING_WORD_COUNT_THRESHOLD

    return count_words(text) > word_limit


def validate_summary_length(
    original_text: str, summary_text: str, max_ratio: float = 0.2
) -> bool:
    """
    Validates that a summary meets the length requirement relative to original text.

    Args:
        original_text: The original text that was summarized
        summary_text: The generated summary text
        max_ratio: Maximum allowed ratio of summary to original text (default: 0.2)

    Returns:
        bool: True if summary meets length requirement, False otherwise
    """
    original_word_count = count_words(original_text)
    summary_word_count = count_words(summary_text)
    max_allowed_words = int(original_word_count * max_ratio)

    return summary_word_count <= max_allowed_words


def format_summary_section(summary_text: str) -> str:
    """
    Formats a summary text with proper heading and structure for journal entries.

    Creates a properly formatted summary section with a Markdown heading and
    appropriate spacing. This ensures consistent formatting across all journal
    entries that include summaries.

    Args:
        summary_text: The summary text to format

    Returns:
        str: Formatted summary section with heading and proper spacing

    Raises:
        ValueError: If summary_text is empty or contains only whitespace
    """
    if not summary_text or not summary_text.strip():
        raise ValueError("Cannot format empty summary text")

    # Clean up the summary text
    clean_summary = summary_text.strip()

    # Create the formatted section with Markdown heading
    formatted_section = f"### Summary\n\n{clean_summary}"

    return formatted_section


def generate_summary(text: str, max_summary_ratio: Optional[float] = None) -> str:
    """
    Generate a concise summary of the journal entry using AI.

    Uses configurable summary ratio and minimum word requirements from settings.

    Args:
        text: The journal entry text to summarize
        max_summary_ratio: Optional custom summary ratio. If None, uses settings.JOURNALING_SUMMARY_RATIO

    Returns:
        str: The generated summary text

    Raises:
        ValueError: If the text is empty or too short to meaningfully summarize
        OSError: If the AI model is unavailable or API calls fail
    """
    if max_summary_ratio is None:
        max_summary_ratio = settings.JOURNALING_SUMMARY_RATIO

    min_words = settings.JOURNALING_SUMMARY_MIN_WORDS

    # Validate input
    if not text or not text.strip():
        raise ValueError("Cannot summarize empty text")

    word_count = count_words(text)
    if word_count < min_words:
        raise ValueError(
            f"Text must have at least {min_words} words to generate meaningful summary. "
            f"Current text has {word_count} words."
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
        from langchain_core.messages import HumanMessage
        from core.llm import get_model

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

        # Validate summary length meets the ratio requirement
        if not validate_summary_length(text, summary, max_summary_ratio):
            summary_word_count = count_words(summary)
            max_allowed_words = int(word_count * max_summary_ratio)

            # Log a warning but don't fail - AI models sometimes exceed guidelines
            import warnings

            warnings.warn(
                f"Generated summary ({summary_word_count} words) exceeds target "
                f"length ({max_allowed_words} words) for {word_count}-word entry."
            )

        return summary

    except Exception as e:
        # Re-raise with more context
        if "API" in str(e) or "model" in str(e).lower():
            raise OSError(f"Failed to generate summary due to AI model error: {e}")
        else:
            raise OSError(f"Unexpected error during summary generation: {e}")


def generate_formatted_summary(text: str, max_summary_ratio: float = 0.2) -> str:
    """
    Generates and formats a complete summary section for journal entries.

    Combines summary generation and formatting into a single function that
    produces a ready-to-use summary section with proper Markdown heading.

    Args:
        text: The journal entry text to summarize
        max_summary_ratio: Maximum ratio of summary to original text (default: 0.2)

    Returns:
        str: Complete formatted summary section with heading

    Raises:
        ValueError: If the text is empty or too short to meaningfully summarize
        OSError: If the AI model is unavailable or API calls fail
    """
    # Generate the summary
    summary = generate_summary(text, max_summary_ratio)

    # Format it with proper heading
    formatted_summary = format_summary_section(summary)

    return formatted_summary


def save_journal_entry_with_summary(
    content: str,
    custom_date: Optional[datetime] = None,
    force_summary: bool = False,
    max_summary_ratio: Optional[float] = None,
) -> str:
    """
    Save a journal entry with automatic summarization based on configuration.

    Uses settings to determine when summarization should be applied and with what parameters.

    Args:
        content: The journal entry content to save
        custom_date: Optional datetime for the entry (defaults to current time)
        force_summary: Force summarization even if below word threshold
        max_summary_ratio: Optional custom summary ratio. If None, uses settings.JOURNALING_SUMMARY_RATIO

    Returns:
        str: Status message indicating what was saved and any summarization performed

    Raises:
        OSError: If file operations fail or directory cannot be created
        ValueError: If content is empty
    """
    if not content or not content.strip():
        raise ValueError("Cannot save empty journal entry")

    if custom_date is None:
        custom_date = datetime.now()

    # Check if summarization is enabled and if content meets criteria
    should_summarize = settings.JOURNALING_ENABLE_SUMMARIZATION and (
        force_summary or exceeds_word_limit(content)
    )

    # Apply configuration settings
    if max_summary_ratio is None:
        max_summary_ratio = settings.JOURNALING_SUMMARY_RATIO

    # Prepare the entry content
    entry_content = content.strip()

    # Check if summarization is needed
    needs_summary = should_summarize
    word_count = count_words(entry_content)

    if needs_summary:
        try:
            # Generate and format the summary
            formatted_summary = generate_formatted_summary(
                entry_content, max_summary_ratio
            )

            # Append summary to the entry
            entry_content_with_summary = f"{entry_content}\n\n{formatted_summary}"

            # Save the entry with summary
            file_path = add_timestamp_entry(
                entry_content_with_summary, custom_date.date(), custom_date.time()
            )

            return (
                f"Journal entry saved to {file_path}. "
                f"Entry was {word_count} words, so a summary was automatically added. 📝✨"
            )

        except Exception as e:
            # If summarization fails, save without summary but log the issue
            import warnings

            warnings.warn(
                f"Failed to generate summary: {e}. Saving entry without summary."
            )

            file_path = add_timestamp_entry(
                entry_content, custom_date.date(), custom_date.time()
            )

            return (
                f"Journal entry saved to {file_path}. "
                f"Entry was {word_count} words but summary generation failed. "
                f"Entry saved without summary. 📝⚠️"
            )
    else:
        # Save entry without summary
        file_path = add_timestamp_entry(
            entry_content, custom_date.date(), custom_date.time()
        )

        return (
            f"Journal entry saved to {file_path}. "
            f"Entry was {word_count} words (under {settings.JOURNALING_WORD_COUNT_THRESHOLD} word limit). 📝"
        )


def parse_frontmatter(file_path: str) -> Dict[str, Any]:
    """
    Parse YAML frontmatter from a journal file.

    Frontmatter is expected to be at the beginning of the file, delimited by '---'
    lines. Returns the parsed frontmatter as a dictionary.

    Args:
        file_path: Absolute path to the journal file

    Returns:
        Dict[str, Any]: Parsed frontmatter data, empty dict if no frontmatter found

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        OSError: If file operations fail
        yaml.YAMLError: If frontmatter contains invalid YAML
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Journal file does not exist: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file starts with frontmatter delimiter
        if not content.startswith("---\n"):
            return {}

        # Find the closing delimiter
        try:
            end_delimiter_pos = content.index("\n---\n", 4)
        except ValueError:
            # No closing delimiter found, invalid frontmatter
            return {}

        # Extract frontmatter content (between delimiters)
        frontmatter_content = content[4:end_delimiter_pos]

        # Parse YAML
        try:
            frontmatter_data = yaml.safe_load(frontmatter_content)
            return frontmatter_data if frontmatter_data else {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in frontmatter: {e}")

    except OSError as e:
        raise OSError(f"Failed to read file {file_path}: {e}")


def extract_content_without_frontmatter(file_path: str) -> str:
    """
    Extract the main content from a journal file, excluding frontmatter.

    Args:
        file_path: Absolute path to the journal file

    Returns:
        str: The main content without frontmatter

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        OSError: If file operations fail
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Journal file does not exist: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file starts with frontmatter
        if not content.startswith("---\n"):
            return content

        # Find the closing delimiter
        try:
            end_delimiter_pos = content.index("\n---\n", 4)
            # Return content after the closing delimiter and newline
            return content[end_delimiter_pos + 5 :]
        except ValueError:
            # No closing delimiter found, return original content
            return content

    except OSError as e:
        raise OSError(f"Failed to read file {file_path}: {e}")


def update_frontmatter(file_path: str, metadata: Dict[str, Any]) -> None:
    """
    Update or add frontmatter to a journal file.

    Args:
        file_path: Absolute path to the journal file
        metadata: Dictionary of metadata to add/update in frontmatter

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        OSError: If file operations fail
        yaml.YAMLError: If metadata cannot be serialized to YAML
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Journal file does not exist: {file_path}")

    try:
        # Get existing frontmatter and content
        existing_frontmatter = parse_frontmatter(file_path)
        main_content = extract_content_without_frontmatter(file_path)

        # Merge existing frontmatter with new metadata
        updated_frontmatter = {**existing_frontmatter, **metadata}

        # Generate YAML frontmatter
        try:
            yaml_content = yaml.dump(
                updated_frontmatter, default_flow_style=False, sort_keys=True
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to serialize metadata to YAML: {e}")

        # Build the complete file content
        new_content = f"---\n{yaml_content}---\n{main_content}"

        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    except OSError as e:
        raise OSError(f"Failed to update frontmatter in file {file_path}: {e}")


def get_journal_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get metadata from a journal file's frontmatter.

    Returns standardized metadata fields including mood, keywords, topics.

    Args:
        file_path: Absolute path to the journal file

    Returns:
        Dict[str, Any]: Dictionary containing metadata with standardized keys

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        OSError: If file operations fail
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Journal file does not exist: {file_path}")

    try:
        frontmatter = parse_frontmatter(file_path)
        content = extract_content_without_frontmatter(file_path)

        # Extract filename date (YYYY-MM-DD.md format)
        filename = os.path.basename(file_path)
        file_date = filename.replace(".md", "") if filename.endswith(".md") else None

        # Build standardized metadata
        metadata = {
            "mood": frontmatter.get("mood"),
            "keywords": _normalize_list_field(frontmatter.get("keywords", [])),
            "topics": _normalize_list_field(frontmatter.get("topics", [])),
            "tags": _normalize_list_field(frontmatter.get("tags", [])),
            "date": file_date,
            "word_count": count_words(content),
            "file_path": file_path,
        }

        # Add any additional frontmatter fields
        for key, value in frontmatter.items():
            if key not in metadata:
                metadata[key] = value

        return metadata

    except OSError as e:
        raise OSError(f"Failed to get metadata from file {file_path}: {e}")


def _normalize_list_field(field_value: Union[str, List[str], None]) -> List[str]:
    """
    Normalize a field that should be a list of strings.

    Args:
        field_value: The field value to normalize

    Returns:
        List[str]: Normalized list of strings
    """
    if not field_value:
        return []

    if isinstance(field_value, str):
        # Split on commas and clean up whitespace
        return [item.strip() for item in field_value.split(",") if item.strip()]

    if isinstance(field_value, list):
        # Ensure all items are strings and filter out empty ones
        return [str(item).strip() for item in field_value if str(item).strip()]

    return []


def add_metadata_to_entry(
    file_path: str,
    mood: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    **additional_metadata: Any,
) -> None:
    """
    Add metadata to a journal file's frontmatter.

    Args:
        file_path: Absolute path to the journal file
        mood: Mood for the entry (e.g., "happy", "stressed", "calm")
        keywords: List of keywords related to the entry
        topics: List of topics covered in the entry
        tags: List of tags for categorization
        **additional_metadata: Any additional metadata fields

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        OSError: If file operations fail
        yaml.YAMLError: If metadata cannot be serialized
    """
    metadata = {}

    if mood is not None:
        metadata["mood"] = mood

    if keywords is not None:
        metadata["keywords"] = keywords

    if topics is not None:
        metadata["topics"] = topics

    if tags is not None:
        metadata["tags"] = tags

    # Add any additional metadata
    metadata.update(additional_metadata)

    # Only update if we have metadata to add
    if metadata:
        update_frontmatter(file_path, metadata)


def search_by_date_range(
    start_date: Optional[Union[str, date]] = None,
    end_date: Optional[Union[str, date]] = None,
    journal_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for journal entries within a date range.

    Args:
        start_date: Start date (inclusive). Can be string "YYYY-MM-DD" or date object
        end_date: End date (inclusive). Can be string "YYYY-MM-DD" or date object
        journal_dir: Optional custom journal directory path

    Returns:
        List[Dict[str, Any]]: List of journal entries with metadata and file paths

    Raises:
        ValueError: If date parameters are invalid
        OSError: If journal directory cannot be accessed
    """
    if journal_dir is None:
        journal_dir = get_journal_directory()

    if not os.path.exists(journal_dir):
        return []  # No journal directory means no entries

    # Parse and validate date parameters
    parsed_start_date = _parse_date_parameter(start_date) if start_date else None
    parsed_end_date = _parse_date_parameter(end_date) if end_date else None

    # Validate date range
    if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
        raise ValueError("Start date cannot be after end date")

    results = []

    try:
        # Get all .md files in journal directory
        journal_files = []
        for filename in os.listdir(journal_dir):
            if filename.endswith(".md"):
                journal_files.append(filename)

        # Filter and collect matching entries
        for filename in journal_files:
            try:
                # Extract date from filename (YYYY-MM-DD.md format)
                file_date_str = filename.replace(".md", "")
                file_date = _parse_date_parameter(file_date_str)

                # Check if file date is within range
                if _date_in_range(file_date, parsed_start_date, parsed_end_date):
                    file_path = os.path.join(journal_dir, filename)

                    # Get metadata for this file
                    try:
                        metadata = get_journal_metadata(file_path)
                        results.append(metadata)
                    except (OSError, yaml.YAMLError) as e:
                        # Log error but continue with other files
                        warnings.warn(f"Could not read metadata from {filename}: {e}")
                        continue

            except ValueError:
                # Skip files that don't match date format
                continue

    except OSError as e:
        raise OSError(f"Cannot access journal directory {journal_dir}: {e}")

    # Sort results by date (newest first)
    results.sort(key=lambda x: x.get("date", ""), reverse=True)

    return results


def _parse_date_parameter(date_param: Union[str, date]) -> date:
    """
    Parse a date parameter that can be either a string or date object.

    Args:
        date_param: Date as string "YYYY-MM-DD" or date object

    Returns:
        date: Parsed date object

    Raises:
        ValueError: If date string is invalid format
    """
    if isinstance(date_param, date):
        return date_param

    if isinstance(date_param, str):
        try:
            # Parse YYYY-MM-DD format
            year, month, day = date_param.split("-")
            return date(int(year), int(month), int(day))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format '{date_param}'. Expected YYYY-MM-DD")

    raise ValueError(
        f"Date parameter must be string or date object, got {type(date_param)}"
    )


def _date_in_range(
    file_date: date, start_date: Optional[date], end_date: Optional[date]
) -> bool:
    """
    Check if a file date falls within the specified range.

    Args:
        file_date: The date to check
        start_date: Start of range (inclusive), None means no start limit
        end_date: End of range (inclusive), None means no end limit

    Returns:
        bool: True if date is within range
    """
    if start_date and file_date < start_date:
        return False

    if end_date and file_date > end_date:
        return False

    return True


def search_by_keywords(
    keywords: Union[str, List[str]],
    case_sensitive: bool = False,
    search_content: bool = True,
    search_frontmatter: bool = True,
    journal_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for journal entries containing specific keywords.

    Performs full-text search across journal entry content and/or frontmatter.
    Supports both single keyword strings and lists of keywords.

    Args:
        keywords: Keywords to search for (string or list of strings)
        case_sensitive: Whether search should be case sensitive (default: False)
        search_content: Whether to search in main content (default: True)
        search_frontmatter: Whether to search in frontmatter fields (default: True)
        journal_dir: Optional custom journal directory path

    Returns:
        List[Dict[str, Any]]: List of matching journal entries with metadata

    Raises:
        ValueError: If no keywords provided or invalid parameters
        OSError: If journal directory cannot be accessed
    """
    if not keywords:
        raise ValueError("At least one keyword must be provided")

    # Normalize keywords to list
    if isinstance(keywords, str):
        keyword_list = [keywords]
    else:
        keyword_list = list(keywords)

    if not keyword_list or all(not k.strip() for k in keyword_list):
        raise ValueError("Keywords cannot be empty")

    # Clean up keywords
    clean_keywords = [k.strip() for k in keyword_list if k.strip()]

    if journal_dir is None:
        journal_dir = get_journal_directory()

    if not os.path.exists(journal_dir):
        return []  # No journal directory means no entries

    results = []

    try:
        # Get all .md files in journal directory
        journal_files = [f for f in os.listdir(journal_dir) if f.endswith(".md")]

        for filename in journal_files:
            file_path = os.path.join(journal_dir, filename)

            try:
                # Get metadata and content
                metadata = get_journal_metadata(file_path)
                content = extract_content_without_frontmatter(file_path)

                # Check if any keywords match
                if _file_matches_keywords(
                    content,
                    metadata,
                    clean_keywords,
                    case_sensitive,
                    search_content,
                    search_frontmatter,
                ):
                    # Add match score for potential ranking
                    match_score = _calculate_match_score(
                        content,
                        metadata,
                        clean_keywords,
                        case_sensitive,
                        search_content,
                        search_frontmatter,
                    )
                    metadata["match_score"] = match_score
                    results.append(metadata)

            except (OSError, yaml.YAMLError) as e:
                # Log error but continue with other files
                warnings.warn(f"Could not process {filename}: {e}")
                continue

    except OSError as e:
        raise OSError(f"Cannot access journal directory {journal_dir}: {e}")

    # Sort results by match score (highest first), then by date (newest first)
    results.sort(
        key=lambda x: (-x.get("match_score", 0), x.get("date", "")), reverse=True
    )

    return results


def _file_matches_keywords(
    content: str,
    metadata: Dict[str, Any],
    keywords: List[str],
    case_sensitive: bool,
    search_content: bool,
    search_frontmatter: bool,
) -> bool:
    """
    Check if a journal file matches any of the provided keywords.

    Args:
        content: Main content of the journal file
        metadata: File metadata including frontmatter
        keywords: List of keywords to search for
        case_sensitive: Whether search is case sensitive
        search_content: Whether to search main content
        search_frontmatter: Whether to search frontmatter fields

    Returns:
        bool: True if file matches any keyword
    """
    search_text = ""

    # Build search text based on options
    if search_content and content:
        search_text += content

    if search_frontmatter:
        # Include searchable frontmatter fields
        frontmatter_text = _extract_searchable_frontmatter_text(metadata)
        if frontmatter_text:
            search_text += " " + frontmatter_text

    if not search_text.strip():
        return False

    # Prepare text for searching
    if not case_sensitive:
        search_text = search_text.lower()

    # Check if any keyword matches
    for keyword in keywords:
        search_keyword = keyword.lower() if not case_sensitive else keyword
        if search_keyword in search_text:
            return True

    return False


def _extract_searchable_frontmatter_text(metadata: Dict[str, Any]) -> str:
    """
    Extract searchable text from frontmatter metadata.

    Args:
        metadata: File metadata dictionary

    Returns:
        str: Combined searchable text from frontmatter fields
    """
    searchable_text = []

    # Include mood
    if metadata.get("mood"):
        searchable_text.append(str(metadata["mood"]))

    # Include keywords/tags lists
    for field in ["keywords", "topics", "tags"]:
        field_value = metadata.get(field, [])
        if field_value:
            if isinstance(field_value, list):
                searchable_text.extend([str(item) for item in field_value])
            else:
                searchable_text.append(str(field_value))

    # Include other string fields (but skip technical fields)
    skip_fields = {
        "date",
        "word_count",
        "file_path",
        "match_score",
        "mood",
        "keywords",
        "topics",
        "tags",
    }

    for key, value in metadata.items():
        if key not in skip_fields and value:
            if isinstance(value, str):
                searchable_text.append(value)
            elif isinstance(value, list):
                searchable_text.extend([str(item) for item in value])

    return " ".join(searchable_text)


def _calculate_match_score(
    content: str,
    metadata: Dict[str, Any],
    keywords: List[str],
    case_sensitive: bool,
    search_content: bool,
    search_frontmatter: bool,
) -> int:
    """
    Calculate a match score for ranking search results.

    Higher scores indicate better matches. Scoring factors:
    - Number of keyword matches
    - Matches in frontmatter vs content
    - Multiple occurrences of same keyword

    Args:
        content: Main content of the journal file
        metadata: File metadata including frontmatter
        keywords: List of keywords to search for
        case_sensitive: Whether search is case sensitive
        search_content: Whether content was searched
        search_frontmatter: Whether frontmatter was searched

    Returns:
        int: Match score (higher = better match)
    """
    score = 0

    # Prepare search texts
    content_text = content if search_content else ""
    frontmatter_text = (
        _extract_searchable_frontmatter_text(metadata) if search_frontmatter else ""
    )

    if not case_sensitive:
        content_text = content_text.lower()
        frontmatter_text = frontmatter_text.lower()

    for keyword in keywords:
        search_keyword = keyword.lower() if not case_sensitive else keyword

        # Count matches in content (1 point each)
        if content_text:
            content_matches = content_text.count(search_keyword)
            score += content_matches

        # Count matches in frontmatter (2 points each - more specific)
        if frontmatter_text:
            frontmatter_matches = frontmatter_text.count(search_keyword)
            score += frontmatter_matches * 2

    return score
