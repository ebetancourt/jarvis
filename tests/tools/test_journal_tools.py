import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
import pytest
import sys

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
