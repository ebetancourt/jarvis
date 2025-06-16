#!/usr/bin/env python3
"""
Simple test to verify journaling agent is properly registered.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_agent_registry():
    """Test that journaling agent is properly registered in agents.py"""
    print("Testing journaling agent registry...")

    try:
        # Read the agents.py file directly
        agents_file = os.path.join(
            os.path.dirname(__file__), "src", "agents", "agents.py"
        )

        with open(agents_file, "r") as f:
            content = f.read()

        # Check for journaling agent import
        if "from agents.journaling_agent import journaling_agent" in content:
            print("✅ Journaling agent import found")
        else:
            print("❌ Journaling agent import NOT found")
            return False

        # Check for journaling agent in registry
        if '"journaling-agent"' in content and "journaling_agent" in content:
            print("✅ Journaling agent found in registry")
        else:
            print("❌ Journaling agent NOT found in registry")
            return False

        # Check for proper description
        if "A daily journaling assistant with guided prompts" in content:
            print("✅ Correct description found")
        else:
            print("❌ Correct description NOT found")
            return False

        print("✅ All registry checks passed!")
        return True

    except Exception as e:
        print(f"❌ Error reading agents.py: {e}")
        return False


def test_journaling_agent_file():
    """Test that the journaling agent file exists and has basic structure."""
    print("\nTesting journaling agent file structure...")

    try:
        agent_file = os.path.join(
            os.path.dirname(__file__), "src", "agents", "journaling_agent.py"
        )

        if not os.path.exists(agent_file):
            print("❌ Journaling agent file does not exist")
            return False

        print("✅ Journaling agent file exists")

        with open(agent_file, "r") as f:
            content = f.read()

        # Check for key components
        checks = [
            ("@tool", "Tool decorators"),
            ("create_react_agent", "LangGraph agent creation"),
            ("journaling_agent =", "Agent instance"),
            ("save_journal_entry_with_summary", "Core journaling function"),
            ("search_by_", "Search functionality"),
            ("Luna", "Agent personality name"),
        ]

        all_passed = True
        for check, description in checks:
            if check in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} NOT found")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"❌ Error reading journaling agent file: {e}")
        return False


def test_tools_file():
    """Test that the journal tools file exists and has expected functions."""
    print("\nTesting journal tools file...")

    try:
        tools_file = os.path.join(
            os.path.dirname(__file__), "src", "tools", "journal_tools.py"
        )

        if not os.path.exists(tools_file):
            print("❌ Journal tools file does not exist")
            return False

        print("✅ Journal tools file exists")

        with open(tools_file, "r") as f:
            content = f.read()

        # Check for key functions
        functions = [
            "create_daily_file",
            "add_timestamp_entry",
            "save_journal_entry_with_summary",
            "search_by_date_range",
            "search_by_keywords",
            "search_by_mood",
            "search_by_topics",
            "parse_frontmatter",
            "get_journal_metadata",
        ]

        all_found = True
        for func in functions:
            if f"def {func}(" in content:
                print(f"✅ Function {func} found")
            else:
                print(f"❌ Function {func} NOT found")
                all_found = False

        return all_found

    except Exception as e:
        print(f"❌ Error reading journal tools file: {e}")
        return False


def main():
    """Run all simple tests."""
    print("=" * 60)
    print("JOURNALING AGENT SIMPLE INTEGRATION TESTS")
    print("=" * 60)

    results = []

    # Test 1: Agent Registry
    results.append(test_agent_registry())

    # Test 2: Agent File Structure
    results.append(test_journaling_agent_file())

    # Test 3: Tools File
    results.append(test_tools_file())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All integration tests PASSED!")
        print("✅ Journaling agent is properly set up and ready for use.")
        print("\nThe journaling agent should be:")
        print("• Visible in agent selection interfaces")
        print("• Accessible via get_agent('journaling-agent')")
        print("• Ready for testing with the streamlit app")
    else:
        print("⚠️  Some tests failed. Please check the output above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
