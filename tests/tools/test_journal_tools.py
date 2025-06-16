import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
import pytest
import sys
import yaml

# Add src to path for importing the source modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tools.journal_tools import (
    ensure_journal_directory,
    get_journal_directory,
    create_daily_file,
    format_file_title,
    add_timestamp_entry,
    append_to_existing_file,
    check_disk_space,
    check_directory_permissions,
    count_words,
    exceeds_word_limit,
    generate_summary,
    validate_summary_length,
    format_summary_section,
    generate_formatted_summary,
    save_journal_entry_with_summary,
    parse_frontmatter,
    extract_content_without_frontmatter,
    update_frontmatter,
    get_journal_metadata,
    add_metadata_to_entry,
    _normalize_list_field,
    search_by_date_range,
    _parse_date_parameter,
    _date_in_range,
    search_by_keywords,
    _extract_searchable_frontmatter_text,
    _calculate_match_score,
    search_by_mood,
    search_by_topics,
)


class TestJournalDirectoryFunctions:
    """Test cases for journal directory management functions."""

    def test_ensure_journal_directory_creates_directory(self):
        """Test that ensure_journal_directory creates the journal directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock DATA_DIR to point to our temporary directory
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Call the function
                result_path = ensure_journal_directory()

                # Verify the directory was created
                expected_path = Path(temp_dir) / "journal"
                assert expected_path.exists()
                assert expected_path.is_dir()
                assert result_path == str(expected_path.absolute())

    def test_ensure_journal_directory_sets_permissions(self):
        """Test that ensure_journal_directory sets proper permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Call the function
                ensure_journal_directory()

                journal_dir = Path(temp_dir) / "journal"
                # Check permissions (this may vary by OS)
                mode = journal_dir.stat().st_mode
                # At minimum, owner should have read/write permissions
                assert mode & 0o700  # Owner has read/write/execute

    def test_ensure_journal_directory_handles_existing_directory(self):
        """Test that function works correctly when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Pre-create the directory
            journal_dir = Path(temp_dir) / "journal"
            journal_dir.mkdir(parents=True, exist_ok=True)

            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Call the function
                result_path = ensure_journal_directory()

                # Verify it still works
                assert journal_dir.exists()
                assert result_path == str(journal_dir.absolute())

    def test_get_journal_directory_returns_correct_path(self):
        """Test that get_journal_directory returns the correct path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                result_path = get_journal_directory()
                expected_path = os.path.join(temp_dir, "journal")
                assert result_path == expected_path

    def test_ensure_journal_directory_raises_on_permission_error(self):
        """Test that function raises PermissionError when chmod fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Mock os.chmod to raise PermissionError
                with patch(
                    "tools.journal_tools.os.chmod",
                    side_effect=PermissionError("Permission denied"),
                ):
                    with pytest.raises(
                        PermissionError, match="Unable to create or set permissions"
                    ):
                        ensure_journal_directory()

    def test_ensure_journal_directory_raises_on_os_error(self):
        """Test that function raises OSError when mkdir fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Mock mkdir to raise OSError
                with patch.object(Path, "mkdir", side_effect=OSError("Disk full")):
                    with pytest.raises(
                        OSError, match="Failed to create journal directory"
                    ):
                        ensure_journal_directory()

    def test_create_daily_file_default_date(self):
        """Test that create_daily_file creates a file with today's date."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Call the function with default date
                result_path = create_daily_file()

                # Verify the file was created with today's date
                today = date.today()
                expected_filename = f"{today.strftime('%Y-%m-%d')}.md"
                expected_path = os.path.join(temp_dir, "journal", expected_filename)

                assert result_path == expected_path
                assert os.path.exists(result_path)

    def test_create_daily_file_custom_date(self):
        """Test that create_daily_file creates a file with a custom date."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Call the function with a custom date
                test_date = date(2025, 1, 9)
                result_path = create_daily_file(test_date)

                # Verify the file was created with the custom date
                expected_filename = "2025-01-09.md"
                expected_path = os.path.join(temp_dir, "journal", expected_filename)

                assert result_path == expected_path
                assert os.path.exists(result_path)

    def test_create_daily_file_existing_file(self):
        """Test that create_daily_file returns existing file path if file exists."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 9)

                # Create the file first time
                path1 = create_daily_file(test_date)

                # Create the file second time - should return same path
                path2 = create_daily_file(test_date)

                assert path1 == path2
                assert os.path.exists(path1)

    def test_create_daily_file_filename_format(self):
        """Test that create_daily_file generates correct YYYY-MM-DD.md format."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Test various date formats
                test_cases = [
                    (date(2025, 1, 9), "2025-01-09.md"),
                    (date(2024, 12, 25), "2024-12-25.md"),
                    (date(2023, 6, 30), "2023-06-30.md"),
                ]

                for test_date, expected_filename in test_cases:
                    result_path = create_daily_file(test_date)
                    assert result_path.endswith(expected_filename)
                    assert os.path.exists(result_path)

    def test_create_daily_file_creates_journal_directory(self):
        """Test that create_daily_file creates journal directory if it doesn't exist."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Ensure journal directory doesn't exist initially
                journal_dir = os.path.join(temp_dir, "journal")
                assert not os.path.exists(journal_dir)

                # Call create_daily_file
                result_path = create_daily_file(date(2025, 1, 9))

                # Verify journal directory was created
                assert os.path.exists(journal_dir)
                assert os.path.exists(result_path)

    def test_format_file_title_default_date(self):
        """Test that format_file_title formats today's date correctly."""
        from datetime import date

        # Call the function with default date
        result = format_file_title()
        today = date.today()

        # Verify the format contains expected components
        assert result.startswith("# ")
        assert today.strftime("%A") in result  # Day of week
        assert today.strftime("%B") in result  # Month name
        assert today.strftime("%Y") in result  # Year
        assert " of " in result

    def test_format_file_title_custom_date(self):
        """Test that format_file_title formats a custom date correctly."""
        from datetime import date

        # Call the function with a specific date
        test_date = date(2025, 6, 13)  # Friday, 13th of June 2025
        result = format_file_title(test_date)

        # Verify the exact format
        expected = "# Friday, 13th of June 2025"
        assert result == expected

    def test_format_file_title_ordinal_suffixes(self):
        """Test that format_file_title generates correct ordinal suffixes."""
        from datetime import date

        # Test various ordinal suffixes
        test_cases = [
            (date(2025, 1, 1), "1st"),
            (date(2025, 1, 2), "2nd"),
            (date(2025, 1, 3), "3rd"),
            (date(2025, 1, 4), "4th"),
            (date(2025, 1, 11), "11th"),  # Special case
            (date(2025, 1, 12), "12th"),  # Special case
            (date(2025, 1, 13), "13th"),  # Special case
            (date(2025, 1, 21), "21st"),
            (date(2025, 1, 22), "22nd"),
            (date(2025, 1, 23), "23rd"),
            (date(2025, 1, 31), "31st"),
        ]

        for test_date, expected_suffix in test_cases:
            result = format_file_title(test_date)
            assert expected_suffix in result

    def test_format_file_title_different_months_and_years(self):
        """Test that format_file_title handles different months and years."""
        from datetime import date

        test_cases = [
            (date(2023, 12, 25), "# Monday, 25th of December 2023"),
            (date(2024, 7, 4), "# Thursday, 4th of July 2024"),
            (date(2025, 1, 1), "# Wednesday, 1st of January 2025"),
        ]

        for test_date, expected in test_cases:
            result = format_file_title(test_date)
            assert result == expected

    def test_format_file_title_format_structure(self):
        """Test that format_file_title maintains consistent format structure."""
        from datetime import date

        # Test with any date
        test_date = date(2025, 3, 15)
        result = format_file_title(test_date)

        # Verify structure: "# <Day>, <Date> of <Month> <Year>"
        parts = result.split()
        assert parts[0] == "#"
        assert parts[1].endswith(",")  # Day of week with comma
        assert " of " in result
        assert len(parts) >= 5  # Should have at least "# Day, Date of Month Year"

    def test_add_timestamp_entry_new_file(self):
        """Test that add_timestamp_entry creates a new file with title and entry."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 9)
                test_time = time(14, 30, 45)
                test_content = "This is my first journal entry."

                # Call the function
                result_path = add_timestamp_entry(test_content, test_date, test_time)

                # Verify the file was created and has correct content
                assert os.path.exists(result_path)

                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Verify content includes title, timestamp, and entry
                assert "# Thursday, 9th of January 2025" in content
                assert "## 14:30:45" in content
                assert test_content in content

    def test_add_timestamp_entry_append_to_existing(self):
        """Test that add_timestamp_entry appends to existing file correctly."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 9)
                test_time1 = time(9, 0, 0)
                test_time2 = time(17, 30, 0)
                test_content1 = "Morning entry."
                test_content2 = "Evening entry."

                # Add first entry
                result_path1 = add_timestamp_entry(test_content1, test_date, test_time1)

                # Add second entry
                result_path2 = add_timestamp_entry(test_content2, test_date, test_time2)

                # Should be the same file
                assert result_path1 == result_path2

                # Verify content has both entries
                with open(result_path1, "r", encoding="utf-8") as f:
                    content = f.read()

                assert "## 09:00:00" in content
                assert test_content1 in content
                assert "## 17:30:00" in content
                assert test_content2 in content
                # Title should only appear once
                assert content.count("# Thursday, 9th of January 2025") == 1

    def test_add_timestamp_entry_default_parameters(self):
        """Test that add_timestamp_entry works with default date and time."""
        from datetime import date, datetime

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_content = "Entry with default parameters."

                # Get current date/time for comparison
                before_call = datetime.now()
                result_path = add_timestamp_entry(test_content)
                after_call = datetime.now()

                # Verify file was created
                assert os.path.exists(result_path)

                # Verify filename contains today's date
                today = date.today()
                expected_filename = f"{today.strftime('%Y-%m-%d')}.md"
                assert result_path.endswith(expected_filename)

                # Verify content
                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert test_content in content
                # Should have a timestamp between before and after the call
                assert "## " in content  # Some timestamp should be present

    def test_add_timestamp_entry_custom_date_time(self):
        """Test that add_timestamp_entry works with custom date and time."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2024, 12, 31)
                test_time = time(23, 59, 59)
                test_content = "Last entry of the year!"

                result_path = add_timestamp_entry(test_content, test_date, test_time)

                # Verify correct filename
                assert result_path.endswith("2024-12-31.md")

                # Verify content
                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert "# Tuesday, 31st of December 2024" in content
                assert "## 23:59:59" in content
                assert test_content in content

    def test_add_timestamp_entry_file_structure(self):
        """Test that add_timestamp_entry creates proper file structure."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 9)
                test_time = time(12, 0, 0)
                test_content = "Test entry for structure verification."

                result_path = add_timestamp_entry(test_content, test_date, test_time)

                with open(result_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Verify structure:
                # Line 0: Title (# ...)
                # Line 1: Empty line
                # Line 2: Timestamp (## ...)
                # Line 3: Empty line
                # Line 4+: Content
                assert lines[0].startswith("# ")
                assert lines[1].strip() == ""
                assert lines[2].startswith("## ")
                assert lines[3].strip() == ""
                assert test_content in "".join(lines[4:])

    def test_add_timestamp_entry_multiple_entries_structure(self):
        """Test that multiple entries maintain proper structure."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 9)

                # Add multiple entries
                add_timestamp_entry("First entry", test_date, time(9, 0, 0))
                add_timestamp_entry("Second entry", test_date, time(12, 0, 0))
                result_path = add_timestamp_entry(
                    "Third entry", test_date, time(18, 0, 0)
                )

                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Should have proper spacing between entries
                sections = content.split("\n\n")
                # Should have title, then entry blocks separated by double newlines
                assert len(sections) >= 3  # Title + at least 2 entries

                # Verify all timestamps are present
                assert "## 09:00:00" in content
                assert "## 12:00:00" in content
                assert "## 18:00:00" in content

                # Verify all content is present
                assert "First entry" in content
                assert "Second entry" in content
                assert "Third entry" in content

    def test_append_to_existing_file_with_content(self):
        """Test that append_to_existing_file adds content with proper spacing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create initial file with content
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Initial content")

            # Append new content
            new_content = "New content"
            append_to_existing_file(test_file, new_content)

            # Verify the result
            with open(test_file, "r", encoding="utf-8") as f:
                result = f.read()

            expected = "Initial content\n\nNew content"
            assert result == expected

    def test_append_to_existing_file_empty_file(self):
        """Test that append_to_existing_file handles empty files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "empty.md")

            # Create empty file
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("")

            # Append content
            new_content = "First content"
            append_to_existing_file(test_file, new_content)

            # Verify the result
            with open(test_file, "r", encoding="utf-8") as f:
                result = f.read()

            assert result == new_content

    def test_append_to_existing_file_nonexistent_file(self):
        """Test that append_to_existing_file raises FileNotFoundError for missing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "nonexistent.md")

            with pytest.raises(FileNotFoundError):
                append_to_existing_file(test_file, "Some content")

    def test_append_to_existing_file_proper_spacing(self):
        """Test that append_to_existing_file maintains proper spacing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "spacing.md")

            # Create file with content that has trailing whitespace
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Initial content   \n\n  ")

            # Append new content
            append_to_existing_file(test_file, "New content")

            # Verify proper spacing
            with open(test_file, "r", encoding="utf-8") as f:
                result = f.read()

            # Should strip existing content and add proper spacing
            expected = "Initial content\n\nNew content"
            assert result == expected

    def test_append_to_existing_file_multiline_content(self):
        """Test that append_to_existing_file handles multiline content correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "multiline.md")

            # Create initial file
            initial_content = "Line 1\nLine 2"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(initial_content)

            # Append multiline content
            new_content = "New line 1\nNew line 2\nNew line 3"
            append_to_existing_file(test_file, new_content)

            # Verify the result
            with open(test_file, "r", encoding="utf-8") as f:
                result = f.read()

            expected = f"{initial_content}\n\n{new_content}"
            assert result == expected

    def test_check_disk_space_sufficient_space(self):
        """Test check_disk_space returns True when sufficient space is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with a very small requirement (1 byte)
            result = check_disk_space(temp_dir, 1)
            assert result is True

    def test_check_disk_space_minimal_requirement(self):
        """Test check_disk_space with default requirement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with default 1MB requirement
            result = check_disk_space(temp_dir)
            assert isinstance(result, bool)

    def test_check_disk_space_invalid_path(self):
        """Test check_disk_space handles invalid paths gracefully."""
        # Test with a non-existent path
        result = check_disk_space("/definitely/does/not/exist")
        assert result is True  # Should return True when can't check

    def test_check_directory_permissions_readable_directory(self):
        """Test check_directory_permissions with a readable directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            readable, writable, executable = check_directory_permissions(temp_dir)
            # Temporary directory should be readable and writable
            assert readable is True
            assert writable is True
            # Executable might vary by system, so we don't assert it

    def test_check_directory_permissions_nonexistent_directory(self):
        """Test check_directory_permissions with nonexistent directory."""
        readable, writable, executable = check_directory_permissions(
            "/definitely/does/not/exist"
        )
        assert readable is False
        assert writable is False
        assert executable is False

    def test_enhanced_permission_error_handling(self):
        """Test enhanced error handling for permission issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Mock check_directory_permissions to return no write permission
                with patch(
                    "tools.journal_tools.check_directory_permissions"
                ) as mock_check:
                    mock_check.return_value = (True, False, True)  # No write permission

                    with pytest.raises(
                        PermissionError,
                        match="No write permission for parent directory",
                    ):
                        ensure_journal_directory()

    def test_enhanced_disk_space_error_handling(self):
        """Test enhanced error handling for disk space issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Mock check_disk_space to return insufficient space
                with patch("tools.journal_tools.check_disk_space") as mock_check:
                    mock_check.return_value = False

                    with pytest.raises(
                        OSError,
                        match="Insufficient disk space to create journal directory",
                    ):
                        ensure_journal_directory()

    def test_create_daily_file_disk_space_error(self):
        """Test create_daily_file with insufficient disk space."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Mock check_disk_space to return insufficient space for file creation
                with patch("tools.journal_tools.check_disk_space") as mock_check:
                    # Return True for directory creation, False for file creation
                    mock_check.side_effect = [True, False]

                    with pytest.raises(
                        OSError, match="Insufficient disk space to create journal file"
                    ):
                        create_daily_file(date(2025, 1, 9))

    def test_create_daily_file_permission_error(self):
        """Test create_daily_file with permission errors."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # First create the journal directory
                ensure_journal_directory()

                # Mock check_directory_permissions to return no write permission
                with patch(
                    "tools.journal_tools.check_directory_permissions"
                ) as mock_check:
                    # Return False for write permission during file creation
                    mock_check.return_value = (True, False, True)

                    with pytest.raises(
                        PermissionError,
                        match="No write permission for journal directory",
                    ):
                        create_daily_file(date(2025, 1, 9))

    def test_append_to_existing_file_permission_errors(self):
        """Test append_to_existing_file with various permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create a test file
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Initial content")

            # Test read permission error
            with patch("tools.journal_tools.os.access") as mock_access:
                # Mock no read permission
                mock_access.side_effect = lambda path, mode: mode != os.R_OK

                with pytest.raises(
                    PermissionError, match="No read permission for file"
                ):
                    append_to_existing_file(test_file, "New content")

            # Test write permission error
            with patch("tools.journal_tools.os.access") as mock_access:
                # Mock no write permission
                mock_access.side_effect = lambda path, mode: mode != os.W_OK

                with pytest.raises(
                    PermissionError, match="No write permission for file"
                ):
                    append_to_existing_file(test_file, "New content")

    def test_append_to_existing_file_disk_space_error(self):
        """Test append_to_existing_file with insufficient disk space."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create a test file
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Initial content")

            # Mock check_disk_space to return insufficient space
            with patch("tools.journal_tools.check_disk_space") as mock_check:
                mock_check.return_value = False

                with pytest.raises(
                    OSError, match="Insufficient disk space to append to file"
                ):
                    append_to_existing_file(test_file, "New content")


class TestWordCounting:
    """Test cases for word counting and limit checking functions."""

    def test_count_words_basic_text(self):
        """Test count_words with basic text."""
        test_cases = [
            ("Hello world", 2),
            ("This is a test", 4),
            ("Single", 1),
            ("One two three four five", 5),
        ]

        for text, expected_count in test_cases:
            result = count_words(text)
            assert result == expected_count, f"Failed for '{text}'"

    def test_count_words_empty_and_whitespace(self):
        """Test count_words with empty strings and whitespace."""
        test_cases = [
            ("", 0),
            ("   ", 0),
            ("\t\n\r", 0),
            ("  \n  \t  ", 0),
        ]

        for text, expected_count in test_cases:
            result = count_words(text)
            assert result == expected_count, f"Failed for '{text}'"

    def test_count_words_multiple_spaces(self):
        """Test count_words with multiple consecutive spaces."""
        test_cases = [
            ("hello    world", 2),
            ("  leading spaces", 2),
            ("trailing spaces  ", 2),
            ("  both  sides  ", 2),
            ("lots     of        spaces", 3),
        ]

        for text, expected_count in test_cases:
            result = count_words(text)
            assert result == expected_count, f"Failed for '{text}'"

    def test_count_words_newlines_and_tabs(self):
        """Test count_words with newlines and tabs."""
        test_cases = [
            ("hello\nworld", 2),
            ("line1\nline2\nline3", 3),
            ("tab\tseparated\twords", 3),
            ("mixed\n\ttabs and\n\nnewlines", 4),
            ("\nhello\n\nworld\n", 2),
        ]

        for text, expected_count in test_cases:
            result = count_words(text)
            assert result == expected_count, f"Failed for '{text}'"

    def test_count_words_punctuation(self):
        """Test count_words with punctuation (should be counted as part of words)."""
        test_cases = [
            ("Hello, world!", 2),
            ("Don't count this wrong.", 4),
            ("What's the weather?", 3),
            ("It's a beautiful day, isn't it?", 6),
            ("Email: test@example.com works fine.", 4),
        ]

        for text, expected_count in test_cases:
            result = count_words(text)
            assert result == expected_count, f"Failed for '{text}'"

    def test_count_words_journal_entry_example(self):
        """Test count_words with realistic journal entry text."""
        short_entry = """Today was a productive day. I completed several tasks
        and felt accomplished."""
        assert count_words(short_entry) == 12

        longer_entry = """I had a challenging day at work today. There were
        several meetings that ran longer than expected, and I found myself
        struggling to keep up with all the tasks on my plate. However, I
        managed to prioritize the most important items and made significant
        progress on the key project."""
        assert count_words(longer_entry) == 49

    def test_exceeds_word_limit_default_limit(self):
        """Test exceeds_word_limit with default 150-word limit."""
        # Create a text with exactly 150 words
        words_150 = " ".join([f"word{i}" for i in range(150)])
        assert not exceeds_word_limit(words_150)  # Exactly 150, should not exceed

        # Create a text with 151 words
        words_151 = words_150 + " extra"
        assert exceeds_word_limit(words_151)  # Should exceed

        # Create a text with fewer than 150 words
        words_100 = " ".join([f"word{i}" for i in range(100)])
        assert not exceeds_word_limit(words_100)  # Should not exceed

    def test_exceeds_word_limit_custom_limit(self):
        """Test exceeds_word_limit with custom word limits."""
        test_text = "This is a test with exactly seven words."
        assert count_words(test_text) == 8  # Verify our count

        # Test with different limits
        assert not exceeds_word_limit(test_text, word_limit=10)  # Under limit
        assert not exceeds_word_limit(test_text, word_limit=8)  # At limit
        assert exceeds_word_limit(test_text, word_limit=7)  # Over limit
        assert exceeds_word_limit(test_text, word_limit=5)  # Well over limit

    def test_exceeds_word_limit_edge_cases(self):
        """Test exceeds_word_limit with edge cases."""
        # Empty text
        assert not exceeds_word_limit("")
        assert not exceeds_word_limit("   ")

        # Single word
        assert not exceeds_word_limit("Hello", word_limit=1)
        assert exceeds_word_limit("Hello", word_limit=0)

        # Whitespace handling
        assert not exceeds_word_limit("  hello   world  ", word_limit=2)
        assert exceeds_word_limit("  hello   world  ", word_limit=1)

    def test_exceeds_word_limit_realistic_journal_entries(self):
        """Test exceeds_word_limit with realistic journal entries."""
        # Short entry (under 150 words)
        short_entry = """Today was good. I accomplished most of my goals and
        felt productive. Looking forward to tomorrow."""
        assert not exceeds_word_limit(short_entry)

        # Create an entry that's definitely over 150 words
        long_entry = """Today was an incredibly complex and challenging day that
        required me to juggle multiple responsibilities while maintaining focus
        on long-term goals. I started the morning with a comprehensive review
        of my task list, prioritizing items based on both urgency and importance.
        The first major challenge came during the team meeting when we discovered
        significant issues with the current project timeline. This led to an
        extended discussion about resource allocation and potential solutions.
        I found myself taking on additional responsibilities to help address
        the gaps we identified. Throughout the afternoon, I worked diligently
        on both immediate priorities and strategic planning for next week.
        By evening, I had made substantial progress on most fronts, though
        I recognize there's still significant work ahead. Overall, despite
        the challenges, I feel satisfied with today's accomplishments and
        optimistic about moving forward with renewed energy and clearer direction
        for the coming days. This additional text brings us well over the
        one hundred and fifty word limit that we need to exceed for testing
        the summarization threshold functionality correctly."""

        assert exceeds_word_limit(long_entry)
        # Verify it's actually over 150 words
        assert count_words(long_entry) > 150

    def test_word_counting_integration(self):
        """Test integration between count_words and exceeds_word_limit."""
        test_cases = [
            ("Short text", 2, False),
            (" ".join(["word"] * 149), 149, False),
            (" ".join(["word"] * 150), 150, False),
            (" ".join(["word"] * 151), 151, True),
            (" ".join(["word"] * 200), 200, True),
        ]

        for text, expected_count, should_exceed in test_cases:
            word_count = count_words(text)
            exceeds = exceeds_word_limit(text)

            assert (
                word_count == expected_count
            ), f"Word count failed for {len(text.split())} words"
            assert (
                exceeds == should_exceed
            ), f"Exceed check failed for {word_count} words"


class TestSummarization:
    """Test cases for AI-powered summarization functions."""

    def test_generate_summary_empty_input(self):
        """Test that generate_summary raises ValueError for empty input."""
        test_cases = ["", "   ", "\t\n\r"]

        for empty_text in test_cases:
            with pytest.raises(ValueError, match="Cannot summarize empty text"):
                generate_summary(empty_text)

        # Test None separately
        with pytest.raises(ValueError, match="Cannot summarize empty text"):
            generate_summary(None)

    def test_generate_summary_too_short_input(self):
        """Test that generate_summary raises ValueError for very short input."""
        short_texts = [
            "Short.",
            "Too short",
            "This is only five words",
            "Just a few words here",
        ]

        for short_text in short_texts:
            word_count = count_words(short_text)
            if word_count < 20:
                with pytest.raises(
                    ValueError, match="Text is too short to meaningfully summarize"
                ):
                    generate_summary(short_text)

    @patch("langchain_aws.ChatBedrock")  # Mock the problematic import
    @patch("core.llm.get_model")
    def test_generate_summary_basic_functionality(self, mock_get_model, mock_bedrock):
        """Test that generate_summary works with valid input."""
        long_entry = """Today was a complex day filled with both challenges and victories.
        I started the morning feeling anxious about the big presentation I had to give at work.
        The preparation took longer than expected, and I found myself rushing to get everything
        ready. However, when it came time to present, everything went smoothly. My colleagues
        asked thoughtful questions and seemed genuinely interested in the project. After the
        presentation, I felt a huge sense of relief and accomplishment. The rest of the day
        was spent catching up on emails and planning for next week. I'm grateful for how
        things turned out and proud of how I handled the pressure."""

        # Mock the model and its response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = "Had anxiety about work presentation but it went well. Felt relief and accomplishment afterward."
        mock_model.invoke.return_value = mock_response
        mock_get_model.return_value = mock_model

        result = generate_summary(long_entry)

        # Verify the function was called and returned a summary
        assert isinstance(result, str)
        assert len(result) > 0
        assert len(result) < len(long_entry)
        mock_model.invoke.assert_called_once()

    @patch("langchain_aws.ChatBedrock")
    @patch("core.llm.get_model")
    def test_generate_summary_custom_ratio(self, mock_get_model, mock_bedrock):
        """Test generate_summary with custom summary ratio."""
        test_entry = " ".join([f"word{i}" for i in range(100)])

        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = "This is a test summary."
        mock_model.invoke.return_value = mock_response
        mock_get_model.return_value = mock_model

        result = generate_summary(test_entry, max_summary_ratio=0.1)

        # Verify the prompt includes the correct word count target
        call_args = mock_model.invoke.call_args[0][0][0].content
        assert "10 words" in call_args

    @patch("langchain_aws.ChatBedrock")
    @patch("core.llm.get_model")
    def test_generate_summary_model_error_handling(self, mock_get_model, mock_bedrock):
        """Test that generate_summary handles model errors appropriately."""
        test_entry = "This is a sufficiently long entry with more than twenty words to test error handling when the model fails to respond properly."

        # Test API error
        mock_model = Mock()
        mock_model.invoke.side_effect = Exception("API rate limit exceeded")
        mock_get_model.return_value = mock_model

        with pytest.raises(
            OSError, match="Failed to generate summary due to AI model error"
        ):
            generate_summary(test_entry)

        # Test empty response
        mock_model.invoke.side_effect = None
        mock_response = Mock()
        mock_response.content = ""  # Empty response
        mock_model.invoke.return_value = mock_response

        with pytest.raises(OSError, match="AI model returned empty summary"):
            generate_summary(test_entry)

    def test_validate_summary_length_within_limit(self):
        """Test that validate_summary_length correctly identifies valid summaries."""
        # 100-word original text
        original_text = " ".join([f"word{i}" for i in range(100)])

        # 15-word summary (15% of original, within 20% limit)
        short_summary = " ".join([f"summary{i}" for i in range(15)])

        assert validate_summary_length(original_text, short_summary, 0.2) == True

        # Exactly at limit (20 words = 20% of 100)
        exact_limit_summary = " ".join([f"summary{i}" for i in range(20)])
        assert validate_summary_length(original_text, exact_limit_summary, 0.2) == True

    def test_validate_summary_length_exceeds_limit(self):
        """Test that validate_summary_length correctly identifies summaries that exceed limit."""
        # 100-word original text
        original_text = " ".join([f"word{i}" for i in range(100)])

        # 25-word summary (25% of original, exceeds 20% limit)
        long_summary = " ".join([f"summary{i}" for i in range(25)])

        assert validate_summary_length(original_text, long_summary, 0.2) == False

    def test_validate_summary_length_custom_ratios(self):
        """Test validate_summary_length with different ratio settings."""
        original_text = " ".join([f"word{i}" for i in range(200)])  # 200 words

        # Test with 10% ratio
        summary_15_words = " ".join([f"summary{i}" for i in range(15)])  # 7.5%
        summary_25_words = " ".join([f"summary{i}" for i in range(25)])  # 12.5%

        assert validate_summary_length(original_text, summary_15_words, 0.1) == True
        assert validate_summary_length(original_text, summary_25_words, 0.1) == False

        # Test with 30% ratio
        summary_50_words = " ".join([f"summary{i}" for i in range(50)])  # 25%
        summary_70_words = " ".join([f"summary{i}" for i in range(70)])  # 35%

        assert validate_summary_length(original_text, summary_50_words, 0.3) == True
        assert validate_summary_length(original_text, summary_70_words, 0.3) == False

    def test_validate_summary_length_edge_cases(self):
        """Test validate_summary_length with edge cases."""
        # Very short original text
        short_original = "This is short text."  # 4 words
        summary = "Short summary."  # 2 words (50%)

        # With 20% ratio, 2 words should fail (20% of 4 = 0.8, rounds to 0)
        assert validate_summary_length(short_original, summary, 0.2) == False

        # With 60% ratio, 2 words should pass
        assert validate_summary_length(short_original, summary, 0.6) == True

        # Empty summary
        assert validate_summary_length(short_original, "", 0.2) == True

        # Empty original
        assert validate_summary_length("", "summary", 0.2) == False

    def test_format_summary_section_basic_formatting(self):
        """Test that format_summary_section creates proper Markdown format."""
        summary_text = "This is a test summary with important insights."

        result = format_summary_section(summary_text)

        # Check the formatted structure
        expected = "### Summary\n\nThis is a test summary with important insights."
        assert result == expected

        # Check that it starts with the heading
        assert result.startswith("### Summary\n\n")

        # Check that the summary text is included
        assert summary_text in result

    def test_format_summary_section_whitespace_handling(self):
        """Test that format_summary_section handles whitespace correctly."""
        # Test with leading/trailing whitespace
        summary_with_whitespace = "   This summary has extra whitespace.   \n\n"

        result = format_summary_section(summary_with_whitespace)

        # Should trim whitespace but preserve the content
        expected = "### Summary\n\nThis summary has extra whitespace."
        assert result == expected

    def test_format_summary_section_multiline_text(self):
        """Test format_summary_section with multiline summary text."""
        multiline_summary = """This is a longer summary.

        It spans multiple lines and includes various insights about the day."""

        result = format_summary_section(multiline_summary)

        # Should preserve the multiline structure
        assert result.startswith("### Summary\n\n")
        assert "This is a longer summary." in result
        assert "It spans multiple lines" in result
        assert "insights about the day." in result

    def test_format_summary_section_empty_input(self):
        """Test that format_summary_section raises ValueError for empty input."""
        test_cases = ["", "   ", "\t\n\r", None]

        for empty_text in test_cases:
            if empty_text is None:
                with pytest.raises(
                    ValueError, match="Cannot format empty summary text"
                ):
                    format_summary_section(empty_text)
            else:
                with pytest.raises(
                    ValueError, match="Cannot format empty summary text"
                ):
                    format_summary_section(empty_text)

    def test_format_summary_section_special_characters(self):
        """Test format_summary_section with special characters and formatting."""
        summary_with_special = "Summary with *emphasis*, **bold**, and `code` elements."

        result = format_summary_section(summary_with_special)

        # Should preserve Markdown formatting within the summary
        expected = (
            "### Summary\n\nSummary with *emphasis*, **bold**, and `code` elements."
        )
        assert result == expected

    def test_format_summary_section_consistency(self):
        """Test that format_summary_section produces consistent output."""
        test_summary = "Consistent formatting test summary."

        # Call multiple times to ensure consistency
        result1 = format_summary_section(test_summary)
        result2 = format_summary_section(test_summary)
        result3 = format_summary_section(test_summary)

        # All results should be identical
        assert result1 == result2 == result3

        # And should match expected format
        expected = "### Summary\n\nConsistent formatting test summary."
        assert result1 == expected


class TestIntegratedWorkflow:
    """Test cases for the integrated workflow with summarization."""

    def test_save_journal_entry_short_entry_no_summary(self):
        """Test saving a short entry that doesn't require summarization."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                short_entry = "Today was a good day. I accomplished my main goals."
                test_date = date(2025, 1, 10)
                test_time = time(15, 30, 0)

                result = save_journal_entry_with_summary(
                    short_entry, test_date, test_time
                )

                # Verify success message indicates no summary needed
                assert "under 150 word limit" in result
                assert "📝" in result

                # Verify file was created and contains entry without summary
                file_path = os.path.join(temp_dir, "journal", "2025-01-10.md")
                assert os.path.exists(file_path)

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert short_entry in content
                assert "### Summary" not in content
                assert "## 15:30:00" in content

    @patch("tools.journal_tools.get_model")
    def test_save_journal_entry_long_entry_with_summary(self, mock_get_model):
        """Test saving a long entry that triggers automatic summarization."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Create a long entry (over 150 words)
                long_entry = " ".join([f"word{i}" for i in range(200)])
                test_date = date(2025, 1, 10)
                test_time = time(16, 45, 0)

                # Mock the AI response
                mock_model = Mock()
                mock_response = Mock()
                mock_response.content = "This is a test summary of the long entry."
                mock_model.invoke.return_value = mock_response
                mock_get_model.return_value = mock_model

                result = save_journal_entry_with_summary(
                    long_entry, test_date, test_time
                )

                # Verify success message indicates summary was added
                assert "summary was automatically added" in result
                assert "📝✨" in result
                assert "200 words" in result

                # Verify file was created and contains entry with summary
                file_path = os.path.join(temp_dir, "journal", "2025-01-10.md")
                assert os.path.exists(file_path)

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert long_entry in content
                assert "### Summary" in content
                assert "This is a test summary" in content
                assert "## 16:45:00" in content

    def test_save_journal_entry_empty_content_error(self):
        """Test that empty content raises appropriate error."""
        test_cases = ["", "   ", "\t\n\r"]

        for empty_content in test_cases:
            with pytest.raises(ValueError, match="Cannot save empty journal entry"):
                save_journal_entry_with_summary(empty_content)

    @patch("tools.journal_tools.get_model")
    def test_save_journal_entry_summary_failure_fallback(self, mock_get_model):
        """Test graceful fallback when summary generation fails."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                long_entry = " ".join([f"word{i}" for i in range(200)])
                test_date = date(2025, 1, 10)
                test_time = time(17, 0, 0)

                # Mock the AI to raise an exception
                mock_model = Mock()
                mock_model.invoke.side_effect = Exception("AI service unavailable")
                mock_get_model.return_value = mock_model

                with patch("warnings.warn") as mock_warn:
                    result = save_journal_entry_with_summary(
                        long_entry, test_date, test_time
                    )

                # Verify warning was issued and entry saved without summary
                mock_warn.assert_called_once()
                assert "summary generation failed" in result
                assert "📝⚠️" in result

                # Verify file was created without summary
                file_path = os.path.join(temp_dir, "journal", "2025-01-10.md")
                assert os.path.exists(file_path)

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert long_entry in content
                assert "### Summary" not in content

    def test_save_journal_entry_default_datetime(self):
        """Test saving with default date and time parameters."""
        from datetime import date, datetime

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                entry = "Today's reflection with default timestamp."

                before_call = datetime.now()
                result = save_journal_entry_with_summary(entry)
                after_call = datetime.now()

                # Should save successfully
                assert "Journal entry saved" in result
                assert "📝" in result

                # Verify file exists with today's date
                today = date.today()
                expected_filename = f"{today.strftime('%Y-%m-%d')}.md"

                # Check that a file was created for today
                journal_dir = os.path.join(temp_dir, "journal")
                files = os.listdir(journal_dir) if os.path.exists(journal_dir) else []
                assert expected_filename in files

                # Verify content includes our entry
                file_path = os.path.join(journal_dir, expected_filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert entry in content

    def test_save_journal_entry_custom_word_limit_and_ratio(self):
        """Test saving with custom word limit and summary ratio parameters."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Entry with exactly 100 words
                entry_100_words = " ".join([f"word{i}" for i in range(100)])
                test_date = date(2025, 1, 10)
                test_time = time(18, 0, 0)

                # Test with custom limit of 50 words (should trigger summary)
                result = save_journal_entry_with_summary(
                    entry_100_words,
                    test_date,
                    test_time,
                    word_limit=50,
                    summary_ratio=0.1,
                )

                # Should indicate summary was needed due to custom limit
                assert "summary was automatically added" in result
                assert "100 words" in result

    def test_save_journal_entry_conversation_flow_integration(self):
        """Test integration with typical conversation flow content."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                # Simulate conversation flow output
                conversation_content = """Today was quite challenging but ultimately rewarding.

Reflection 1: I felt overwhelmed in the morning when I saw my long task list, but I managed to prioritize and focus on the most important items.

Reflection 2: I learned that breaking down big tasks into smaller chunks really helps me feel less anxious and more in control of my day."""

                test_date = date(2025, 1, 10)
                test_time = time(19, 30, 0)

                result = save_journal_entry_with_summary(
                    conversation_content, test_date, test_time
                )

                # Verify successful save
                assert "Journal entry saved" in result
                assert "📝" in result

                # Verify file content preserves conversation structure
                file_path = os.path.join(temp_dir, "journal", "2025-01-10.md")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                assert "Today was quite challenging" in content
                assert "Reflection 1:" in content
                assert "Reflection 2:" in content
                assert "## 19:30:00" in content


class TestConfigurationIntegration:
    """Test cases for configuration integration from core.settings."""

    def test_exceeds_word_limit_uses_settings_default(self):
        """Test that exceeds_word_limit uses settings.JOURNALING_WORD_COUNT_THRESHOLD by default."""
        from core.settings import settings

        # Test with text that's longer than default threshold (150 words)
        long_text = " ".join(["word"] * 151)
        short_text = " ".join(["word"] * 149)

        # Should use settings default (150)
        assert exceeds_word_limit(long_text) == True
        assert exceeds_word_limit(short_text) == False

        # Verify it's actually using the settings value
        assert exceeds_word_limit(long_text) == (
            count_words(long_text) > settings.JOURNALING_WORD_COUNT_THRESHOLD
        )

    def test_exceeds_word_limit_custom_override(self):
        """Test that exceeds_word_limit accepts custom word limit override."""
        text = " ".join(["word"] * 100)

        # Test with custom limit
        assert exceeds_word_limit(text, word_limit=50) == True
        assert exceeds_word_limit(text, word_limit=150) == False

    @patch("core.llm.get_model")
    def test_generate_summary_uses_settings_defaults(self, mock_get_model):
        """Test that generate_summary uses settings for ratio and min words."""
        from core.settings import settings

        # Mock the AI response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = "Test summary"
        mock_model.invoke.return_value = mock_response
        mock_get_model.return_value = mock_model

        # Create text that meets minimum requirements
        min_words = settings.JOURNALING_SUMMARY_MIN_WORDS
        test_text = " ".join(["word"] * (min_words + 10))

        result = generate_summary(test_text)

        # Should not raise an error and return summary
        assert result == "Test summary"

        # Verify it uses the settings min_words threshold
        short_text = " ".join(["word"] * (min_words - 1))
        with pytest.raises(ValueError, match=f"at least {min_words} words"):
            generate_summary(short_text)

    @patch("core.llm.get_model")
    def test_generate_summary_custom_ratio_override(self, mock_get_model):
        """Test that generate_summary accepts custom ratio override."""
        # Mock the AI response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = "Custom ratio summary"
        mock_model.invoke.return_value = mock_response
        mock_get_model.return_value = mock_model

        test_text = " ".join(["word"] * 50)

        # Test with custom ratio
        result = generate_summary(test_text, max_summary_ratio=0.1)
        assert result == "Custom ratio summary"

    def test_save_journal_entry_respects_settings(self):
        """Test that save_journal_entry_with_summary respects configuration settings."""
        from core.settings import settings

        # Create test content that's exactly at the threshold
        threshold = settings.JOURNALING_WORD_COUNT_THRESHOLD
        content_at_threshold = " ".join(["word"] * threshold)
        content_over_threshold = " ".join(["word"] * (threshold + 1))
        content_under_threshold = " ".join(["word"] * (threshold - 1))

        # Test under threshold (should not attempt summarization)
        with patch("tools.journal_tools.add_timestamp_entry") as mock_add:
            mock_add.return_value = "/test/path.md"

            result = save_journal_entry_with_summary(content_under_threshold)

            assert "under" in result.lower()
            assert str(threshold) in result
            assert "📝" in result

    def test_configuration_validation_in_settings(self):
        """Test that the configuration values in settings have proper validation."""
        from core.settings import Settings
        from pydantic import ValidationError

        # Test invalid word count threshold (too low)
        with pytest.raises(ValidationError):
            Settings(JOURNALING_WORD_COUNT_THRESHOLD=5, _env_file=None)

        # Test invalid word count threshold (too high)
        with pytest.raises(ValidationError):
            Settings(JOURNALING_WORD_COUNT_THRESHOLD=2000, _env_file=None)

        # Test invalid summary ratio (too low)
        with pytest.raises(ValidationError):
            Settings(JOURNALING_SUMMARY_RATIO=0.0, _env_file=None)

        # Test invalid summary ratio (too high)
        with pytest.raises(ValidationError):
            Settings(JOURNALING_SUMMARY_RATIO=1.5, _env_file=None)

    def test_settings_environment_variable_integration(self):
        """Test that environment variables properly configure journaling settings."""
        from core.settings import Settings
        import os
        from unittest.mock import patch

        # Test environment variable override
        with patch.dict(
            os.environ,
            {
                "JOURNALING_WORD_COUNT_THRESHOLD": "200",
                "JOURNALING_SUMMARY_RATIO": "0.3",
                "JOURNALING_ENABLE_SUMMARIZATION": "false",
                "JOURNALING_SUMMARY_MIN_WORDS": "30",
                "JOURNALING_MAX_SUMMARY_ATTEMPTS": "5",
            },
        ):
            test_settings = Settings(_env_file=None)

            assert test_settings.JOURNALING_WORD_COUNT_THRESHOLD == 200
            assert test_settings.JOURNALING_SUMMARY_RATIO == 0.3
            assert test_settings.JOURNALING_ENABLE_SUMMARIZATION == False
            assert test_settings.JOURNALING_SUMMARY_MIN_WORDS == 30
            assert test_settings.JOURNALING_MAX_SUMMARY_ATTEMPTS == 5


class TestFrontmatterParsing:
    """Test cases for frontmatter parsing and metadata functionality."""

    def test_parse_frontmatter_valid_yaml(self):
        """Test parsing valid YAML frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file with frontmatter
            content = """---
mood: happy
keywords:
  - work
  - productivity
topics: ["project management", "team meeting"]
---

# Test Entry

This is a test journal entry."""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = parse_frontmatter(test_file)

            assert result["mood"] == "happy"
            assert result["keywords"] == ["work", "productivity"]
            assert result["topics"] == ["project management", "team meeting"]

    def test_parse_frontmatter_no_frontmatter(self):
        """Test parsing file with no frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file without frontmatter
            content = "# Test Entry\n\nThis is a test journal entry."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = parse_frontmatter(test_file)

            assert result == {}

    def test_parse_frontmatter_invalid_yaml(self):
        """Test parsing file with invalid YAML frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file with invalid YAML
            content = """---
mood: happy
keywords: [unclosed bracket
---

# Test Entry"""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            with pytest.raises(yaml.YAMLError):
                parse_frontmatter(test_file)

    def test_parse_frontmatter_incomplete_delimiters(self):
        """Test parsing file with incomplete frontmatter delimiters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file with only opening delimiter
            content = """---
mood: happy
keywords: work

# Test Entry without closing delimiter"""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = parse_frontmatter(test_file)

            assert result == {}  # Should return empty dict for incomplete frontmatter

    def test_extract_content_without_frontmatter_with_frontmatter(self):
        """Test extracting content from file with frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            content = """---
mood: happy
keywords: ["work"]
---

# Test Entry

This is the main content."""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = extract_content_without_frontmatter(test_file)

            expected = """
# Test Entry

This is the main content."""

            assert result.strip() == expected.strip()

    def test_extract_content_without_frontmatter_no_frontmatter(self):
        """Test extracting content from file without frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            content = "# Test Entry\n\nThis is the main content."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = extract_content_without_frontmatter(test_file)

            assert result == content

    def test_update_frontmatter_add_to_existing(self):
        """Test updating frontmatter in file that already has frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file with existing frontmatter
            content = """---
mood: neutral
keywords: ["old"]
---

# Test Entry"""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Update frontmatter
            new_metadata = {"mood": "happy", "topics": ["new topic"]}
            update_frontmatter(test_file, new_metadata)

            # Verify the update
            updated_frontmatter = parse_frontmatter(test_file)
            assert updated_frontmatter["mood"] == "happy"
            assert updated_frontmatter["keywords"] == [
                "old"
            ]  # Should preserve existing
            assert updated_frontmatter["topics"] == ["new topic"]

    def test_update_frontmatter_add_to_no_frontmatter(self):
        """Test adding frontmatter to file that has none."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file without frontmatter
            content = "# Test Entry\n\nOriginal content."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Add frontmatter
            metadata = {"mood": "excited", "keywords": ["first", "time"]}
            update_frontmatter(test_file, metadata)

            # Verify frontmatter was added
            result_frontmatter = parse_frontmatter(test_file)
            assert result_frontmatter["mood"] == "excited"
            assert result_frontmatter["keywords"] == ["first", "time"]

            # Verify content is preserved
            result_content = extract_content_without_frontmatter(test_file)
            assert "# Test Entry" in result_content
            assert "Original content." in result_content

    def test_get_journal_metadata_with_frontmatter(self):
        """Test getting standardized metadata from file with frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "2025-01-10.md")

            content = """---
mood: productive
keywords: [work, coding, testing]
topics: ["software development"]
custom_field: "custom value"
---

# Test Entry

This is a test entry with multiple words for counting."""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = get_journal_metadata(test_file)

            assert result["mood"] == "productive"
            assert result["keywords"] == ["work", "coding", "testing"]
            assert result["topics"] == ["software development"]
            assert result["tags"] == []  # Default empty
            assert result["date"] == "2025-01-10"
            assert result["word_count"] > 0
            assert result["file_path"] == test_file
            assert (
                result["custom_field"] == "custom value"
            )  # Additional fields preserved

    def test_get_journal_metadata_no_frontmatter(self):
        """Test getting metadata from file without frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "2025-01-11.md")

            content = "# Simple Entry\n\nThis is a simple entry without frontmatter."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = get_journal_metadata(test_file)

            assert result["mood"] is None
            assert result["keywords"] == []
            assert result["topics"] == []
            assert result["tags"] == []
            assert result["date"] == "2025-01-11"
            assert result["word_count"] > 0
            assert result["file_path"] == test_file

    def test_normalize_list_field_string_input(self):
        """Test normalizing comma-separated string to list."""
        test_cases = [
            ("one, two, three", ["one", "two", "three"]),
            ("single", ["single"]),
            ("  spaced  ,  values  ", ["spaced", "values"]),
            ("trailing,comma,", ["trailing", "comma"]),
            ("", []),
            ("   ", []),
        ]

        for input_value, expected in test_cases:
            result = _normalize_list_field(input_value)
            assert result == expected

    def test_normalize_list_field_list_input(self):
        """Test normalizing list input."""
        test_cases = [
            (["one", "two"], ["one", "two"]),
            ([1, 2, 3], ["1", "2", "3"]),  # Numbers converted to strings
            (["  spaced  ", "", "valid"], ["spaced", "valid"]),  # Empty filtered out
            ([], []),
        ]

        for input_value, expected in test_cases:
            result = _normalize_list_field(input_value)
            assert result == expected

    def test_normalize_list_field_none_input(self):
        """Test normalizing None input."""
        result = _normalize_list_field(None)
        assert result == []

    def test_add_metadata_to_entry_new_metadata(self):
        """Test adding metadata to entry with no existing frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            content = "# Test Entry\n\nContent without metadata."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Add metadata
            add_metadata_to_entry(
                test_file,
                mood="focused",
                keywords=["productivity", "goals"],
                topics=["work", "planning"],
                custom_field="test value",
            )

            # Verify metadata was added
            metadata = get_journal_metadata(test_file)
            assert metadata["mood"] == "focused"
            assert metadata["keywords"] == ["productivity", "goals"]
            assert metadata["topics"] == ["work", "planning"]
            assert metadata["custom_field"] == "test value"

    def test_add_metadata_to_entry_update_existing(self):
        """Test updating metadata in entry with existing frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            # Create file with existing frontmatter
            content = """---
mood: neutral
keywords: ["old"]
---

# Test Entry"""

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Update with new metadata
            add_metadata_to_entry(test_file, mood="excited", topics=["new", "topics"])

            # Verify updates
            metadata = get_journal_metadata(test_file)
            assert metadata["mood"] == "excited"  # Updated
            assert metadata["keywords"] == ["old"]  # Preserved
            assert metadata["topics"] == ["new", "topics"]  # Added

    def test_add_metadata_to_entry_no_metadata_provided(self):
        """Test that no changes are made when no metadata is provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.md")

            original_content = "# Test Entry\n\nOriginal content."

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(original_content)

            # Call with no metadata
            add_metadata_to_entry(test_file)

            # Verify no changes were made
            with open(test_file, "r", encoding="utf-8") as f:
                result_content = f.read()

            assert result_content == original_content

    def test_frontmatter_error_handling_nonexistent_file(self):
        """Test error handling for non-existent files."""
        nonexistent_file = "/path/that/does/not/exist.md"

        with pytest.raises(FileNotFoundError):
            parse_frontmatter(nonexistent_file)

        with pytest.raises(FileNotFoundError):
            extract_content_without_frontmatter(nonexistent_file)

        with pytest.raises(FileNotFoundError):
            update_frontmatter(nonexistent_file, {"mood": "test"})

        with pytest.raises(FileNotFoundError):
            get_journal_metadata(nonexistent_file)


class TestDateRangeSearch:
    """Test cases for date range search functionality."""

    def test_search_by_date_range_basic_functionality(self):
        """Test basic date range search with multiple journal files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                journal_dir = os.path.join(temp_dir, "journal")
                os.makedirs(journal_dir, exist_ok=True)

                # Create test journal files
                test_files = [
                    ("2025-01-10.md", "# Entry 1\nContent for Jan 10"),
                    ("2025-01-15.md", "# Entry 2\nContent for Jan 15"),
                    ("2025-01-20.md", "# Entry 3\nContent for Jan 20"),
                    ("2025-02-01.md", "# Entry 4\nContent for Feb 1"),
                ]

                for filename, content in test_files:
                    with open(os.path.join(journal_dir, filename), "w") as f:
                        f.write(content)

                # Test search within range
                results = search_by_date_range("2025-01-12", "2025-01-25")

                # Should find files from Jan 15 and Jan 20
                assert len(results) == 2
                dates = [r["date"] for r in results]
                assert "2025-01-15" in dates
                assert "2025-01-20" in dates
                assert "2025-01-10" not in dates
                assert "2025-02-01" not in dates

    def test_search_by_date_range_with_date_objects(self):
        """Test date range search using date objects instead of strings."""
        from datetime import date

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                journal_dir = os.path.join(temp_dir, "journal")
                os.makedirs(journal_dir, exist_ok=True)

                # Create test files
                test_files = ["2025-01-10.md", "2025-01-15.md", "2025-01-20.md"]

                for filename in test_files:
                    with open(os.path.join(journal_dir, filename), "w") as f:
                        f.write(f"# Entry\nContent for {filename}")

                # Test with date objects
                start_date = date(2025, 1, 12)
                end_date = date(2025, 1, 18)

                results = search_by_date_range(start_date, end_date)

                # Should only find 2025-01-15.md
                assert len(results) == 1
                assert results[0]["date"] == "2025-01-15"

    def test_search_by_date_range_open_ended(self):
        """Test date range search with only start or end date."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                journal_dir = os.path.join(temp_dir, "journal")
                os.makedirs(journal_dir, exist_ok=True)

                # Create test files
                test_files = ["2025-01-10.md", "2025-01-15.md", "2025-01-20.md"]

                for filename in test_files:
                    with open(os.path.join(journal_dir, filename), "w") as f:
                        f.write(f"# Entry\nContent for {filename}")

                # Test with only start date
                results = search_by_date_range(start_date="2025-01-15")
                dates = [r["date"] for r in results]
                assert "2025-01-15" in dates
                assert "2025-01-20" in dates
                assert "2025-01-10" not in dates

                # Test with only end date
                results = search_by_date_range(end_date="2025-01-15")
                dates = [r["date"] for r in results]
                assert "2025-01-10" in dates
                assert "2025-01-15" in dates
                assert "2025-01-20" not in dates

    def test_search_by_date_range_no_results(self):
        """Test date range search that returns no results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                journal_dir = os.path.join(temp_dir, "journal")
                os.makedirs(journal_dir, exist_ok=True)

                # Create test file
                with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                    f.write("# Entry\nContent")

                # Search for dates that don't exist
                results = search_by_date_range("2025-02-01", "2025-02-28")
                assert len(results) == 0

    def test_search_by_date_range_all_files(self):
        """Test date range search with no date constraints."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                journal_dir = os.path.join(temp_dir, "journal")
                os.makedirs(journal_dir, exist_ok=True)

                # Create test files
                test_files = ["2025-01-10.md", "2025-01-15.md", "2025-01-20.md"]

                for filename in test_files:
                    with open(os.path.join(journal_dir, filename), "w") as f:
                        f.write(f"# Entry\nContent for {filename}")

                # Search with no date constraints
                results = search_by_date_range()

                # Should return all files, sorted by date (newest first)
                assert len(results) == 3
                dates = [r["date"] for r in results]
                assert dates == ["2025-01-20", "2025-01-15", "2025-01-10"]

    def test_search_by_date_range_with_frontmatter(self):
        """Test that search includes frontmatter metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                journal_dir = os.path.join(temp_dir, "journal")
                os.makedirs(journal_dir, exist_ok=True)

                # Create file with frontmatter
                content = """---
mood: productive
keywords: [work, coding]
topics: ["software development"]
---

# Daily Entry
Today I worked on search functionality."""

                with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                    f.write(content)

                results = search_by_date_range()

                assert len(results) == 1
                result = results[0]
                assert result["mood"] == "productive"
                assert result["keywords"] == ["work", "coding"]
                assert result["topics"] == ["software development"]
                assert result["word_count"] > 0

    def test_search_by_date_range_invalid_dates(self):
        """Test error handling for invalid date parameters."""
        # Test invalid date format
        with pytest.raises(ValueError, match="Invalid date format"):
            search_by_date_range("invalid-date")

        # Test start date after end date
        with pytest.raises(ValueError, match="Start date cannot be after end date"):
            search_by_date_range("2025-01-20", "2025-01-10")

    def test_search_by_date_range_nonexistent_directory(self):
        """Test search when journal directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use non-existent directory
            fake_dir = os.path.join(temp_dir, "nonexistent")

            results = search_by_date_range(journal_dir=fake_dir)
            assert results == []

    def test_search_by_date_range_malformed_files(self):
        """Test search with malformed journal files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            # Create valid file
            with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                f.write("# Valid Entry\nContent")

            # Create file with invalid date format (should be ignored)
            with open(os.path.join(journal_dir, "invalid-date.md"), "w") as f:
                f.write("# Invalid Entry\nContent")

            # Create non-markdown file (should be ignored)
            with open(os.path.join(journal_dir, "not-markdown.txt"), "w") as f:
                f.write("Not a markdown file")

            results = search_by_date_range(journal_dir=journal_dir)

            # Should only return the valid journal file
            assert len(results) == 1
            assert results[0]["date"] == "2025-01-10"

    def test_parse_date_parameter_string_input(self):
        """Test _parse_date_parameter with string inputs."""
        from datetime import date

        # Valid date strings
        result = _parse_date_parameter("2025-01-10")
        assert result == date(2025, 1, 10)

        # Invalid date strings
        with pytest.raises(ValueError):
            _parse_date_parameter("invalid")

        with pytest.raises(ValueError):
            _parse_date_parameter("2025-13-01")  # Invalid month

    def test_parse_date_parameter_date_object(self):
        """Test _parse_date_parameter with date object input."""
        from datetime import date

        test_date = date(2025, 1, 10)
        result = _parse_date_parameter(test_date)
        assert result == test_date

    def test_parse_date_parameter_invalid_type(self):
        """Test _parse_date_parameter with invalid input types."""
        with pytest.raises(ValueError):
            _parse_date_parameter(12345)

        with pytest.raises(ValueError):
            _parse_date_parameter(None)

    def test_date_in_range_function(self):
        """Test _date_in_range helper function."""
        from datetime import date

        test_date = date(2025, 1, 15)
        start_date = date(2025, 1, 10)
        end_date = date(2025, 1, 20)

        # Date within range
        assert _date_in_range(test_date, start_date, end_date) is True

        # Date before range
        assert _date_in_range(date(2025, 1, 5), start_date, end_date) is False

        # Date after range
        assert _date_in_range(date(2025, 1, 25), start_date, end_date) is False

        # No constraints
        assert _date_in_range(test_date, None, None) is True

        # Only start date constraint
        assert _date_in_range(test_date, start_date, None) is True
        assert _date_in_range(date(2025, 1, 5), start_date, None) is False

        # Only end date constraint
        assert _date_in_range(test_date, None, end_date) is True
        assert _date_in_range(date(2025, 1, 25), None, end_date) is False


class TestKeywordSearch:
    """Test cases for keyword search functionality."""

    def test_search_by_keywords_basic_content_search(self):
        """Test basic keyword search in journal content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            # Create test files with different content
            test_files = [
                (
                    "2025-01-10.md",
                    "# Entry 1\nToday I worked on coding projects and debugging.",
                ),
                (
                    "2025-01-15.md",
                    "# Entry 2\nWent for a walk and enjoyed nature photography.",
                ),
                (
                    "2025-01-20.md",
                    "# Entry 3\nAttended team meetings and worked on project planning.",
                ),
            ]

            for filename, content in test_files:
                with open(os.path.join(journal_dir, filename), "w") as f:
                    f.write(content)

            # Test single keyword search
            results = search_by_keywords("coding", journal_dir=journal_dir)
            assert len(results) == 1
            assert results[0]["date"] == "2025-01-10"

            # Test multiple keyword search
            results = search_by_keywords(
                ["project", "planning"], journal_dir=journal_dir
            )
            assert len(results) == 2
            dates = [r["date"] for r in results]
            assert "2025-01-10" in dates  # "projects"
            assert "2025-01-20" in dates  # "project planning"

    def test_search_by_keywords_frontmatter_search(self):
        """Test keyword search in frontmatter metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            # Create file with frontmatter
            content1 = """---
mood: productive
keywords: [coding, debugging]
topics: ["software development"]
---

# Entry 1
Today was a good day."""

            content2 = """---
mood: relaxed
keywords: [nature, photography]
topics: ["outdoor activities"]
---

# Entry 2
Enjoyed the outdoors."""

            with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                f.write(content1)
            with open(os.path.join(journal_dir, "2025-01-15.md"), "w") as f:
                f.write(content2)

            # Search for frontmatter keywords
            results = search_by_keywords("productive", journal_dir=journal_dir)
            assert len(results) == 1
            assert results[0]["date"] == "2025-01-10"

            # Search for keyword in keywords list
            results = search_by_keywords("photography", journal_dir=journal_dir)
            assert len(results) == 1
            assert results[0]["date"] == "2025-01-15"

            # Search for topic
            results = search_by_keywords("software", journal_dir=journal_dir)
            assert len(results) == 1
            assert results[0]["date"] == "2025-01-10"

    def test_search_by_keywords_case_sensitivity(self):
        """Test case sensitive vs case insensitive search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            content = "# Entry\nToday I worked on CODING projects."
            with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                f.write(content)

            # Case insensitive (default)
            results = search_by_keywords("coding", journal_dir=journal_dir)
            assert len(results) == 1

            results = search_by_keywords("CODING", journal_dir=journal_dir)
            assert len(results) == 1

            # Case sensitive
            results = search_by_keywords(
                "coding", case_sensitive=True, journal_dir=journal_dir
            )
            assert len(results) == 0  # "coding" != "CODING"

            results = search_by_keywords(
                "CODING", case_sensitive=True, journal_dir=journal_dir
            )
            assert len(results) == 1

    def test_search_by_keywords_search_options(self):
        """Test different search scope options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            content = """---
mood: productive
keywords: [frontmatter_keyword]
---

# Entry
This content contains content_keyword."""

            with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                f.write(content)

            # Search only content
            results = search_by_keywords(
                "content_keyword",
                search_content=True,
                search_frontmatter=False,
                journal_dir=journal_dir,
            )
            assert len(results) == 1

            results = search_by_keywords(
                "frontmatter_keyword",
                search_content=True,
                search_frontmatter=False,
                journal_dir=journal_dir,
            )
            assert len(results) == 0

            # Search only frontmatter
            results = search_by_keywords(
                "frontmatter_keyword",
                search_content=False,
                search_frontmatter=True,
                journal_dir=journal_dir,
            )
            assert len(results) == 1

            results = search_by_keywords(
                "content_keyword",
                search_content=False,
                search_frontmatter=True,
                journal_dir=journal_dir,
            )
            assert len(results) == 0

    def test_search_by_keywords_match_scoring(self):
        """Test that results are ranked by match score."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            # File with multiple matches in content
            content1 = "# Entry 1\nCoding coding coding projects."

            # File with frontmatter match (higher score)
            content2 = """---
mood: coding
---

# Entry 2
Working on projects."""

            # File with single content match
            content3 = "# Entry 3\nJust one coding mention."

            files = [
                ("2025-01-10.md", content1),
                ("2025-01-15.md", content2),
                ("2025-01-20.md", content3),
            ]

            for filename, content in files:
                with open(os.path.join(journal_dir, filename), "w") as f:
                    f.write(content)

            results = search_by_keywords("coding", journal_dir=journal_dir)

            # Should have all 3 results
            assert len(results) == 3

            # Check that results have match scores
            for result in results:
                assert "match_score" in result
                assert result["match_score"] > 0

            # Results should be sorted by match score (highest first)
            scores = [r["match_score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_search_by_keywords_empty_results(self):
        """Test search that returns no results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            content = "# Entry\nThis entry has no relevant keywords."
            with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                f.write(content)

            results = search_by_keywords("nonexistent", journal_dir=journal_dir)
            assert len(results) == 0

    def test_search_by_keywords_error_handling(self):
        """Test error handling for invalid parameters."""
        # Empty keywords
        with pytest.raises(ValueError, match="At least one keyword must be provided"):
            search_by_keywords("")

        with pytest.raises(ValueError, match="At least one keyword must be provided"):
            search_by_keywords([])

        with pytest.raises(ValueError, match="Keywords cannot be empty"):
            search_by_keywords(["", "   "])

        # Non-existent directory
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_dir = os.path.join(temp_dir, "nonexistent")
            results = search_by_keywords("test", journal_dir=fake_dir)
            assert results == []

    def test_search_by_keywords_string_vs_list_input(self):
        """Test that string and list inputs work equivalently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            content = "# Entry\nCoding and programming projects."
            with open(os.path.join(journal_dir, "2025-01-10.md"), "w") as f:
                f.write(content)

            # Single string
            results1 = search_by_keywords("coding", journal_dir=journal_dir)

            # List with single item
            results2 = search_by_keywords(["coding"], journal_dir=journal_dir)

            # Results should be identical
            assert len(results1) == len(results2) == 1
            assert results1[0]["date"] == results2[0]["date"]

    def test_search_by_keywords_multiple_files_ranking(self):
        """Test search across multiple files with proper ranking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = temp_dir

            # Different files with varying relevance
            files = [
                ("2025-01-10.md", "# Entry 1\nCoding is fun."),
                ("2025-01-15.md", "# Entry 2\nCoding coding coding everywhere."),
                (
                    "2025-01-20.md",
                    """---
mood: coding
keywords: [coding]
---

# Entry 3
More coding content.""",
                ),
            ]

            for filename, content in files:
                with open(os.path.join(journal_dir, filename), "w") as f:
                    f.write(content)

            results = search_by_keywords("coding", journal_dir=journal_dir)

            # All files should match
            assert len(results) == 3

            # Entry 3 should rank highest (frontmatter + content matches)
            # Entry 2 should be second (multiple content matches)
            # Entry 1 should be third (single content match)
            assert results[0]["date"] == "2025-01-20"  # Highest score
            assert results[1]["date"] == "2025-01-15"  # Multiple matches
            assert results[2]["date"] == "2025-01-10"  # Single match

    def test_extract_searchable_frontmatter_text(self):
        """Test the frontmatter text extraction helper function."""
        metadata = {
            "mood": "happy",
            "keywords": ["work", "productivity"],
            "topics": ["project management"],
            "tags": ["important"],
            "custom_field": "custom value",
            "date": "2025-01-10",  # Should be skipped
            "word_count": 50,  # Should be skipped
            "file_path": "/path",  # Should be skipped
        }

        result = _extract_searchable_frontmatter_text(metadata)

        # Should include all searchable fields
        assert "happy" in result
        assert "work" in result
        assert "productivity" in result
        assert "project management" in result
        assert "important" in result
        assert "custom value" in result

        # Should exclude technical fields
        assert "2025-01-10" not in result
        assert "50" not in result
        assert "/path" not in result

    def test_calculate_match_score(self):
        """Test the match score calculation function."""
        content = "This is about coding and programming and coding again."
        metadata = {"mood": "coding", "keywords": ["programming"], "topics": []}

        # Test score calculation
        score = _calculate_match_score(
            content,
            metadata,
            ["coding", "programming"],
            case_sensitive=False,
            search_content=True,
            search_frontmatter=True,
        )

        # Should have:
        # - 2 "coding" matches in content (2 points)
        # - 1 "programming" match in content (1 point)
        # - 1 "coding" match in frontmatter mood (2 points)
        # - 1 "programming" match in frontmatter keywords (2 points)
        # Total: 2 + 1 + 2 + 2 = 7 points
        assert score == 7


class TestMoodSearch:
    """Test mood-based search functionality."""

    def test_search_by_mood_exact_match(self):
        """Test exact mood matching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with different moods
            happy_file = create_test_file_with_frontmatter(
                temp_dir, "happy.md", "Happy content", {"mood": "happy"}
            )
            productive_file = create_test_file_with_frontmatter(
                temp_dir, "productive.md", "Work content", {"mood": "productive"}
            )
            stressed_file = create_test_file_with_frontmatter(
                temp_dir, "stressed.md", "Stressed content", {"mood": "stressed"}
            )

            # Test exact match
            results = search_by_mood("happy", exact_match=True, journal_dir=temp_dir)

            assert len(results) == 1
            assert results[0]["mood"] == "happy"
            assert "happy.md" in results[0]["file_path"]

    def test_search_by_mood_partial_match(self):
        """Test partial mood matching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file with compound mood
            compound_file = create_test_file_with_frontmatter(
                temp_dir,
                "compound.md",
                "Mixed feelings",
                {"mood": "happy and productive"},
            )

            # Test partial match
            results = search_by_mood("happy", exact_match=False, journal_dir=temp_dir)

            assert len(results) == 1
            assert results[0]["mood"] == "happy and productive"

    def test_search_by_mood_case_insensitive(self):
        """Test case insensitive mood search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            happy_file = create_test_file_with_frontmatter(
                temp_dir, "happy.md", "Happy content", {"mood": "Happy"}
            )

            # Test case insensitive search
            results = search_by_mood("happy", exact_match=True, journal_dir=temp_dir)

            assert len(results) == 1
            assert results[0]["mood"] == "Happy"

    def test_search_by_mood_no_matches(self):
        """Test mood search with no matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sad_file = create_test_file_with_frontmatter(
                temp_dir, "sad.md", "Sad content", {"mood": "sad"}
            )

            # Search for non-existent mood
            results = search_by_mood("happy", journal_dir=temp_dir)

            assert len(results) == 0

    def test_search_by_mood_no_mood_field(self):
        """Test mood search with files that have no mood field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            no_mood_file = create_test_file_with_frontmatter(
                temp_dir, "no_mood.md", "Content without mood", {"keywords": ["test"]}
            )

            results = search_by_mood("happy", journal_dir=temp_dir)

            assert len(results) == 0

    def test_search_by_mood_empty_parameter(self):
        """Test mood search with empty mood parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Mood parameter cannot be empty"):
                search_by_mood("", journal_dir=temp_dir)

    def test_search_by_mood_nonexistent_directory(self):
        """Test mood search with non-existent directory."""
        results = search_by_mood("happy", journal_dir="/nonexistent/path")
        assert len(results) == 0


class TestTopicsSearch:
    """Test topics-based search functionality."""

    def test_search_by_topics_single_topic(self):
        """Test search with single topic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            work_file = create_test_file_with_frontmatter(
                temp_dir,
                "work.md",
                "Work content",
                {"topics": ["work", "productivity"]},
            )
            personal_file = create_test_file_with_frontmatter(
                temp_dir,
                "personal.md",
                "Personal content",
                {"topics": ["personal", "growth"]},
            )

            results = search_by_topics("work", journal_dir=temp_dir)

            assert len(results) == 1
            assert "work" in results[0]["topics"]
            assert "work.md" in results[0]["file_path"]

    def test_search_by_topics_multiple_topics_any_match(self):
        """Test search with multiple topics, any match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            work_file = create_test_file_with_frontmatter(
                temp_dir,
                "work.md",
                "Work content",
                {"topics": ["work", "productivity"]},
            )
            health_file = create_test_file_with_frontmatter(
                temp_dir,
                "health.md",
                "Health content",
                {"topics": ["health", "exercise"]},
            )
            mixed_file = create_test_file_with_frontmatter(
                temp_dir, "mixed.md", "Mixed content", {"topics": ["work", "health"]}
            )

            results = search_by_topics(
                ["work", "exercise"], match_all=False, journal_dir=temp_dir
            )

            # Should match work.md, health.md, and mixed.md
            assert len(results) == 3

    def test_search_by_topics_multiple_topics_all_match(self):
        """Test search with multiple topics, all must match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            work_file = create_test_file_with_frontmatter(
                temp_dir,
                "work.md",
                "Work content",
                {"topics": ["work", "productivity"]},
            )
            mixed_file = create_test_file_with_frontmatter(
                temp_dir,
                "mixed.md",
                "Mixed content",
                {"topics": ["work", "health", "productivity"]},
            )

            results = search_by_topics(
                ["work", "productivity"], match_all=True, journal_dir=temp_dir
            )

            # Should match both files that contain both topics
            assert len(results) == 2

    def test_search_by_topics_case_insensitive(self):
        """Test case insensitive topics search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            work_file = create_test_file_with_frontmatter(
                temp_dir,
                "work.md",
                "Work content",
                {"topics": ["Work", "Productivity"]},
            )

            results = search_by_topics("work", journal_dir=temp_dir)

            assert len(results) == 1
            assert "Work" in results[0]["topics"]

    def test_search_by_topics_scoring(self):
        """Test topics search result scoring."""
        with tempfile.TemporaryDirectory() as temp_dir:
            exact_match_file = create_test_file_with_frontmatter(
                temp_dir,
                "exact.md",
                "Exact match",
                {"topics": ["work", "productivity"]},
            )
            partial_match_file = create_test_file_with_frontmatter(
                temp_dir,
                "partial.md",
                "Partial match",
                {"topics": ["workplace", "efficiency"]},
            )

            results = search_by_topics(["work"], journal_dir=temp_dir)

            # Should have 2 results, exact match should score higher
            assert len(results) == 2
            # Results should be sorted by score (highest first)
            assert results[0]["topic_match_score"] >= results[1]["topic_match_score"]

    def test_search_by_topics_no_matches(self):
        """Test topics search with no matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            work_file = create_test_file_with_frontmatter(
                temp_dir,
                "work.md",
                "Work content",
                {"topics": ["work", "productivity"]},
            )

            results = search_by_topics("travel", journal_dir=temp_dir)

            assert len(results) == 0

    def test_search_by_topics_no_topics_field(self):
        """Test topics search with files that have no topics field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            no_topics_file = create_test_file_with_frontmatter(
                temp_dir, "no_topics.md", "Content without topics", {"mood": "happy"}
            )

            results = search_by_topics("work", journal_dir=temp_dir)

            assert len(results) == 0

    def test_search_by_topics_empty_parameter(self):
        """Test topics search with empty topics parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Topics parameter cannot be empty"):
                search_by_topics("", journal_dir=temp_dir)

            with pytest.raises(ValueError, match="Topics cannot be empty"):
                search_by_topics([], journal_dir=temp_dir)

    def test_search_by_topics_string_input(self):
        """Test topics search with string input (single topic)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            work_file = create_test_file_with_frontmatter(
                temp_dir,
                "work.md",
                "Work content",
                {"topics": ["work", "productivity"]},
            )

            results = search_by_topics("work", journal_dir=temp_dir)

            assert len(results) == 1
            assert "work" in results[0]["topics"]

    def test_search_by_topics_nonexistent_directory(self):
        """Test topics search with non-existent directory."""
        results = search_by_topics("work", journal_dir="/nonexistent/path")
        assert len(results) == 0
