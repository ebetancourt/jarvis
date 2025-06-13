import tempfile
import os
from pathlib import Path
from unittest.mock import patch
import pytest

from tools.journal_tools import (
    ensure_journal_directory,
    get_journal_directory,
    create_daily_file,
    format_file_title,
    add_timestamp_entry,
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
        """Test that format_file_title formats custom dates correctly."""
        from datetime import date

        test_date = date(2025, 6, 13)  # Friday, June 13th, 2025
        result = format_file_title(test_date)

        expected = "# Friday, 13th of June 2025"
        assert result == expected

    def test_format_file_title_ordinal_suffixes(self):
        """Test that format_file_title generates correct ordinal suffixes."""
        from datetime import date

        # Test various ordinal cases
        test_cases = [
            (date(2025, 1, 1), "1st"),  # 1st
            (date(2025, 1, 2), "2nd"),  # 2nd
            (date(2025, 1, 3), "3rd"),  # 3rd
            (date(2025, 1, 4), "4th"),  # 4th
            (date(2025, 1, 11), "11th"),  # 11th (special case)
            (date(2025, 1, 12), "12th"),  # 12th (special case)
            (date(2025, 1, 13), "13th"),  # 13th (special case)
            (date(2025, 1, 21), "21st"),  # 21st
            (date(2025, 1, 22), "22nd"),  # 22nd
            (date(2025, 1, 23), "23rd"),  # 23rd
            (date(2025, 1, 31), "31st"),  # 31st
        ]

        for test_date, expected_ordinal in test_cases:
            result = format_file_title(test_date)
            assert (
                expected_ordinal in result
            ), f"Expected {expected_ordinal} in {result}"

    def test_format_file_title_different_months_and_years(self):
        """Test that format_file_title handles different months and years."""
        from datetime import date

        test_cases = [
            (date(2023, 2, 14), "# Tuesday, 14th of February 2023"),
            (date(2024, 12, 25), "# Wednesday, 25th of December 2024"),
            (date(2025, 7, 4), "# Friday, 4th of July 2025"),
            (date(2026, 11, 1), "# Sunday, 1st of November 2026"),
        ]

        for test_date, expected in test_cases:
            result = format_file_title(test_date)
            assert result == expected

    def test_format_file_title_format_structure(self):
        """Test that format_file_title follows the correct format structure."""
        from datetime import date

        result = format_file_title(date(2025, 6, 13))

        # Should start with "# "
        assert result.startswith("# ")

        # Should contain required separators
        assert ", " in result  # Between day of week and date
        assert " of " in result  # Between date and month
        assert " " in result  # Between month and year

        # Should not contain unexpected characters
        assert "\n" not in result
        assert "\t" not in result

    def test_add_timestamp_entry_new_file(self):
        """Test that add_timestamp_entry creates a new file with title and entry."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 15)
                test_time = time(9, 30, 45)
                content = "This is my first journal entry."

                result_path = add_timestamp_entry(content, test_date, test_time)

                # Verify file was created
                assert os.path.exists(result_path)

                # Read and verify content
                with open(result_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Should contain title, timestamp, and content
                assert "# Wednesday, 15th of January 2025" in file_content
                assert "## 09:30:45" in file_content
                assert content in file_content

    def test_add_timestamp_entry_append_to_existing(self):
        """Test add_timestamp_entry appends to existing file without duplicating title."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 15)

                # Add first entry
                content1 = "First entry of the day."
                time1 = time(9, 30, 45)
                result_path = add_timestamp_entry(content1, test_date, time1)

                # Add second entry
                content2 = "Second entry of the day."
                time2 = time(14, 15, 30)
                result_path2 = add_timestamp_entry(content2, test_date, time2)

                # Should be same file
                assert result_path == result_path2

                # Read and verify content
                with open(result_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Should contain both entries but only one title
                title_count = file_content.count("# Wednesday, 15th of January 2025")
                assert title_count == 1

                assert "## 09:30:45" in file_content
                assert "## 14:15:30" in file_content
                assert content1 in file_content
                assert content2 in file_content

    def test_add_timestamp_entry_default_parameters(self):
        """Test add_timestamp_entry uses current date and time when not specified."""
        from datetime import datetime

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                content = "Entry with default parameters."

                # Mock datetime.now() to control the current time
                mock_now = datetime(2025, 6, 13, 17, 45, 30)
                with patch("tools.journal_tools.datetime") as mock_datetime:
                    mock_datetime.now.return_value = mock_now
                    mock_datetime.side_effect = lambda *args, **kw: datetime(
                        *args, **kw
                    )

                    result_path = add_timestamp_entry(content)

                # Verify file was created with today's date
                assert "2025-06-13.md" in result_path

                # Read and verify content
                with open(result_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Should use current date and time
                assert "# Friday, 13th of June 2025" in file_content
                assert "## 17:45:30" in file_content
                assert content in file_content

    def test_add_timestamp_entry_custom_date_time(self):
        """Test that add_timestamp_entry uses custom date and time correctly."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2024, 12, 25)
                test_time = time(23, 59, 59)
                content = "Christmas evening reflection."

                result_path = add_timestamp_entry(content, test_date, test_time)

                # Verify correct file was created
                assert "2024-12-25.md" in result_path

                # Read and verify content
                with open(result_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                assert "# Wednesday, 25th of December 2024" in file_content
                assert "## 23:59:59" in file_content
                assert content in file_content

    def test_add_timestamp_entry_file_structure(self):
        """Test that add_timestamp_entry creates proper file structure."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 15)
                test_time = time(9, 30, 45)
                content = "Testing file structure."

                result_path = add_timestamp_entry(content, test_date, test_time)

                # Read content and verify structure
                with open(result_path, "r", encoding="utf-8") as f:
                    lines = f.read().split("\n")

                # Expected structure:
                # Line 0: # Title
                # Line 1: Empty
                # Line 2: ## Timestamp
                # Line 3: Empty
                # Line 4: Content
                assert lines[0].startswith("# ")
                assert lines[1] == ""
                assert lines[2].startswith("## ")
                assert lines[3] == ""
                assert lines[4] == content

    def test_add_timestamp_entry_multiple_entries_structure(self):
        """Test file structure with multiple entries."""
        from datetime import date, time

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("tools.journal_tools.DATA_DIR", temp_dir):
                test_date = date(2025, 1, 15)

                # Add first entry
                content1 = "First entry."
                time1 = time(9, 30, 45)
                result_path = add_timestamp_entry(content1, test_date, time1)

                # Add second entry
                content2 = "Second entry."
                time2 = time(14, 15, 30)
                add_timestamp_entry(content2, test_date, time2)

                # Read and verify structure
                with open(result_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Verify proper spacing between entries
                lines = file_content.split("\n")

                # Find the end of first entry and start of second entry
                first_entry_end = -1
                second_entry_start = -1
                for i, line in enumerate(lines):
                    if line == content1:
                        first_entry_end = i
                    if line == "## 14:15:30":
                        second_entry_start = i
                        break

                # Should have empty line between entries
                assert first_entry_end > 0
                assert second_entry_start > 0
                assert lines[first_entry_end + 1] == ""
                assert lines[second_entry_start - 1] == ""
