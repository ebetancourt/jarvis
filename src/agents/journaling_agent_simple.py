from datetime import datetime
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from typing import Optional, List, Dict, Any, Union
from datetime import date

# Import the underlying journal functions
from tools.journal_tools import (
    create_daily_file as _create_daily_file,
    add_timestamp_entry as _add_timestamp_entry,
    save_journal_entry_with_summary as _save_journal_entry_with_summary,
    search_by_date_range as _search_by_date_range,
    search_by_keywords as _search_by_keywords,
    search_by_mood as _search_by_mood,
    search_by_topics as _search_by_topics,
    add_metadata_to_entry as _add_metadata_to_entry,
    get_journal_metadata as _get_journal_metadata,
    count_words as _count_words,
)


# Configure journal tools as LangGraph tools
@tool
def create_daily_file(target_date: Optional[str] = None) -> str:
    """
    Create a new daily journal file.

    Args:
        target_date: Optional date in YYYY-MM-DD format. If not provided, uses today.

    Returns:
        str: Path to the created file and confirmation message.
    """
    from datetime import datetime

    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            return _create_daily_file(parsed_date)
        except ValueError:
            return f"Error: Invalid date format '{target_date}'. Please use YYYY-MM-DD format."

    return _create_daily_file()


@tool
def add_timestamp_entry(content: str, target_date: Optional[str] = None) -> str:
    """
    Add a timestamped journal entry to today's or specified date's journal file.

    Args:
        content: The journal entry content to add.
        target_date: Optional date in YYYY-MM-DD format. If not provided, uses today.

    Returns:
        str: Path to the file and confirmation message.
    """
    from datetime import datetime

    if not content or not content.strip():
        return "Error: Cannot add empty journal entry."

    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            return _add_timestamp_entry(content.strip(), parsed_date)
        except ValueError:
            return f"Error: Invalid date format '{target_date}'. Please use YYYY-MM-DD format."

    return _add_timestamp_entry(content.strip())


@tool
def save_journal_entry_with_summary(
    content: str, target_date: Optional[str] = None, force_summary: bool = False
) -> str:
    """
    Save a journal entry with automatic summarization for long entries.

    Args:
        content: The journal entry content to save.
        target_date: Optional date in YYYY-MM-DD format. If not provided, uses today.
        force_summary: Force summarization even if entry is short.

    Returns:
        str: Status message about what was saved.
    """
    from datetime import datetime

    if not content or not content.strip():
        return "Error: Cannot save empty journal entry."

    custom_date = None
    if target_date:
        try:
            custom_date = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            return f"Error: Invalid date format '{target_date}'. Please use YYYY-MM-DD format."

    return _save_journal_entry_with_summary(
        content.strip(), custom_date=custom_date, force_summary=force_summary
    )


@tool
def search_by_date_range(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> str:
    """
    Search for journal entries within a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format (optional).
        end_date: End date in YYYY-MM-DD format (optional).

    Returns:
        str: Formatted search results with file paths and metadata.
    """
    try:
        results = _search_by_date_range(start_date, end_date)

        if not results:
            date_info = ""
            if start_date and end_date:
                date_info = f" between {start_date} and {end_date}"
            elif start_date:
                date_info = f" from {start_date} onwards"
            elif end_date:
                date_info = f" up to {end_date}"

            return f"No journal entries found{date_info}."

        # Format results
        result_lines = [f"Found {len(results)} journal entries:"]
        for entry in results:
            result_lines.append(
                f"• {entry['date']} - {entry['file_path']} ({entry['word_count']} words)"
            )
            if entry.get("mood"):
                result_lines.append(f"  Mood: {entry['mood']}")
            if entry.get("topics"):
                result_lines.append(f"  Topics: {', '.join(entry['topics'])}")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Error searching by date range: {str(e)}"


@tool
def search_by_keywords(
    keywords: str,
    case_sensitive: bool = False,
    search_content: bool = True,
    search_frontmatter: bool = True,
) -> str:
    """
    Search for journal entries containing specific keywords.

    Args:
        keywords: Keywords to search for (space-separated).
        case_sensitive: Whether search should be case sensitive.
        search_content: Whether to search in entry content.
        search_frontmatter: Whether to search in metadata.

    Returns:
        str: Formatted search results with relevance scores.
    """
    try:
        keyword_list = keywords.strip().split()
        results = _search_by_keywords(
            keyword_list,
            case_sensitive=case_sensitive,
            search_content=search_content,
            search_frontmatter=search_frontmatter,
        )

        if not results:
            return f"No journal entries found containing keywords: {keywords}"

        # Format results with scores
        result_lines = [f"Found {len(results)} entries matching '{keywords}':"]
        for entry in results:
            score = entry.get("match_score", 0)
            result_lines.append(
                f"• {entry['date']} - {entry['file_path']} (score: {score})"
            )
            if entry.get("mood"):
                result_lines.append(f"  Mood: {entry['mood']}")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Error searching by keywords: {str(e)}"


@tool
def search_by_mood(mood: str, exact_match: bool = False) -> str:
    """
    Search for journal entries by mood.

    Args:
        mood: The mood to search for.
        exact_match: Whether to require exact mood match or allow partial matches.

    Returns:
        str: Formatted search results.
    """
    try:
        results = _search_by_mood(mood, exact_match=exact_match)

        if not results:
            match_type = "exactly" if exact_match else "containing"
            return f"No journal entries found with mood {match_type} '{mood}'."

        # Format results
        result_lines = [f"Found {len(results)} entries with mood '{mood}':"]
        for entry in results:
            result_lines.append(
                f"• {entry['date']} - {entry['file_path']} (mood: {entry['mood']})"
            )
            if entry.get("topics"):
                result_lines.append(f"  Topics: {', '.join(entry['topics'])}")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Error searching by mood: {str(e)}"


@tool
def search_by_topics(topics: str, match_all: bool = False) -> str:
    """
    Search for journal entries by topics.

    Args:
        topics: Topics to search for (comma-separated).
        match_all: Whether entry must contain all topics (True) or any topic (False).

    Returns:
        str: Formatted search results with relevance scores.
    """
    try:
        topic_list = [t.strip() for t in topics.split(",")]
        results = _search_by_topics(topic_list, match_all=match_all)

        if not results:
            match_type = "all" if match_all else "any"
            return f"No journal entries found containing {match_type} of these topics: {topics}"

        # Format results with scores
        result_lines = [f"Found {len(results)} entries matching topics '{topics}':"]
        for entry in results:
            score = entry.get("topic_match_score", 0)
            result_lines.append(
                f"• {entry['date']} - {entry['file_path']} (score: {score})"
            )
            result_lines.append(f"  Topics: {', '.join(entry.get('topics', []))}")
            if entry.get("mood"):
                result_lines.append(f"  Mood: {entry['mood']}")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Error searching by topics: {str(e)}"


@tool
def add_metadata_to_entry(
    file_path: str,
    mood: Optional[str] = None,
    keywords: Optional[str] = None,
    topics: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """
    Add metadata to an existing journal entry.

    Args:
        file_path: Path to the journal file.
        mood: Mood to add (optional).
        keywords: Keywords to add, comma-separated (optional).
        topics: Topics to add, comma-separated (optional).
        tags: Tags to add, comma-separated (optional).

    Returns:
        str: Confirmation message.
    """
    try:
        # Convert string lists to actual lists
        kwargs = {}
        if mood:
            kwargs["mood"] = mood.strip()
        if keywords:
            kwargs["keywords"] = [k.strip() for k in keywords.split(",")]
        if topics:
            kwargs["topics"] = [t.strip() for t in topics.split(",")]
        if tags:
            kwargs["tags"] = [t.strip() for t in tags.split(",")]

        _add_metadata_to_entry(file_path, **kwargs)

        added_items = []
        if mood:
            added_items.append(f"mood: {mood}")
        if keywords:
            added_items.append(f"keywords: {keywords}")
        if topics:
            added_items.append(f"topics: {topics}")
        if tags:
            added_items.append(f"tags: {tags}")

        return f"Successfully added metadata to {file_path}: {', '.join(added_items)}"

    except Exception as e:
        return f"Error adding metadata: {str(e)}"


@tool
def get_journal_metadata(file_path: str) -> str:
    """
    Get metadata from a journal entry file.

    Args:
        file_path: Path to the journal file.

    Returns:
        str: Formatted metadata information.
    """
    try:
        metadata = _get_journal_metadata(file_path)

        lines = [f"Metadata for {file_path}:"]
        lines.append(f"Date: {metadata.get('date', 'Unknown')}")
        lines.append(f"Word count: {metadata.get('word_count', 0)}")

        if metadata.get("mood"):
            lines.append(f"Mood: {metadata['mood']}")
        if metadata.get("keywords"):
            lines.append(f"Keywords: {', '.join(metadata['keywords'])}")
        if metadata.get("topics"):
            lines.append(f"Topics: {', '.join(metadata['topics'])}")
        if metadata.get("tags"):
            lines.append(f"Tags: {', '.join(metadata['tags'])}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error getting metadata: {str(e)}"


@tool
def count_words(text: str) -> str:
    """
    Count the number of words in the provided text.

    Args:
        text: The text to count words in.

    Returns:
        str: Word count information.
    """
    try:
        word_count = _count_words(text)
        return f"Word count: {word_count} words"

    except Exception as e:
        return f"Error counting words: {str(e)}"


# Configure tools for the journaling agent
tools = [
    create_daily_file,
    add_timestamp_entry,
    save_journal_entry_with_summary,
    search_by_date_range,
    search_by_keywords,
    search_by_mood,
    search_by_topics,
    add_metadata_to_entry,
    get_journal_metadata,
    count_words,
]

current_date = datetime.now().strftime("%Y-%m-%d")

journaling_agent = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=tools,
    prompt=f"""Today is {current_date}. You are a thoughtful daily journaling assistant
designed to help users reflect on their day and capture meaningful insights.

Your primary role is to guide users through reflective journaling with:

🌟 **Core Functions:**
- Help users create and save journal entries with guided prompts
- Facilitate deeper reflection through CBT-style questioning
- Search and retrieve past journal entries for insights
- Automatically summarize long entries (>150 words)
- Add metadata (mood, topics, keywords) to entries for better organization

📝 **Journaling Approach:**
- Ask thoughtful, open-ended questions that encourage introspection
- Focus on priorities, emotions, growth, and meaningful experiences
- Use a warm, supportive tone that feels like talking to a trusted friend
- Limit follow-up questions to 2 maximum to avoid overwhelming the user
- Detect completion signals like "I'm done" or empty responses

🔍 **Search & Retrieval:**
- Help users find past entries by date, keywords, mood, or topics
- Provide insights by connecting current experiences to past reflections
- Surface relevant memories and patterns from previous entries

💡 **Key Principles:**
- Encourage deeper thinking with questions like "What did you learn?"
- Celebrate small wins and acknowledge challenges
- Respect user boundaries - don't push if they seem finished
- Automatically save entries and add helpful metadata
- Keep the conversation flowing naturally and supportively

Remember: You're not just taking dictation - you're helping users discover
insights about themselves through reflective dialogue.""",
)
