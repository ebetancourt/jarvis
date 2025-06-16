#!/usr/bin/env python3
"""
Test journaling agent import functionality.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_journaling_agent_import():
    """Test that the journaling agent can be imported directly."""
    print("Testing journaling agent import...")

    try:
        # Import the journaling agent directly
        from agents.journaling_agent import journaling_agent

        print("✅ Journaling agent imported successfully")
        print(f"   Agent type: {type(journaling_agent)}")
        return True

    except ImportError as e:
        print(f"❌ Failed to import journaling agent: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing journaling agent: {e}")
        return False


def test_tools_import():
    """Test that journal tools can be imported."""
    print("\nTesting journal tools import...")

    try:
        from tools.journal_tools import (
            create_daily_file,
            save_journal_entry_with_summary,
            search_by_mood,
            search_by_topics,
        )

        print("✅ Journal tools imported successfully")

        # Check that functions are callable
        if callable(create_daily_file):
            print("✅ create_daily_file is callable")
        else:
            print("❌ create_daily_file is not callable")
            return False

        if callable(save_journal_entry_with_summary):
            print("✅ save_journal_entry_with_summary is callable")
        else:
            print("❌ save_journal_entry_with_summary is not callable")
            return False

        return True

    except ImportError as e:
        print(f"❌ Failed to import journal tools: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing journal tools: {e}")
        return False


def main():
    """Run import tests."""
    print("=" * 60)
    print("JOURNALING AGENT IMPORT TESTS")
    print("=" * 60)

    results = []

    # Test 1: Agent Import
    results.append(test_journaling_agent_import())

    # Test 2: Tools Import
    results.append(test_tools_import())

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All import tests PASSED!")
        print("✅ Journaling agent is ready for use in interfaces.")
    else:
        print("⚠️  Some import tests failed.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
