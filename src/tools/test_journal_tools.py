import tempfile
import os
from pathlib import Path
from unittest.mock import patch
import pytest

from tools.journal_tools import (
    ensure_journal_directory,
    get_journal_directory,
    create_daily_file,
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
