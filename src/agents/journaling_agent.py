from datetime import datetime
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from tools.journal_tools import (
    add_metadata_to_entry as _add_metadata_to_entry,
)
from tools.journal_tools import (
    add_timestamp_entry as _add_timestamp_entry,
)
from tools.journal_tools import (
    count_words as _count_words,
)

# Import the underlying journal functions
from tools.journal_tools import (
    create_daily_file as _create_daily_file,
)
from tools.journal_tools import (
    get_journal_metadata as _get_journal_metadata,
)
from tools.journal_tools import (
    save_journal_entry_with_summary as _save_journal_entry_with_summary,
)
from tools.journal_tools import (
    search_by_date_range as _search_by_date_range,
)
from tools.journal_tools import (
    search_by_keywords as _search_by_keywords,
)
from tools.journal_tools import (
    search_by_mood as _search_by_mood,
)
from tools.journal_tools import (
    search_by_topics as _search_by_topics,
)


# Configure journal tools as LangGraph tools
@tool
def create_daily_file(target_date: str | None = None) -> str:
    """
    Create a new daily journal file.

    Args:
        target_date: Optional date in YYYY-MM-DD format. If not provided, uses today.

    Returns:
        str: Path to the created file and confirmation message.
    """
    from datetime import datetime

    try:
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                file_path = _create_daily_file(parsed_date)
                return f"✅ Daily journal file created: {file_path}"
            except ValueError:
                return (
                    f"❌ Error: Invalid date format '{target_date}'. "
                    "Please use YYYY-MM-DD format (e.g., 2024-01-15)."
                )
        else:
            file_path = _create_daily_file()
            return f"✅ Today's journal file created: {file_path}"

    except PermissionError as e:
        return (
            f"❌ Permission denied: {e}. "
            "Please check file system permissions for the journal directory."
        )
    except OSError as e:
        if "space" in str(e).lower():
            return f"❌ Insufficient disk space: {e}. Please free up some disk space and try again."
        elif "read-only" in str(e).lower():
            return f"❌ File system is read-only: {e}. Cannot create journal files."
        else:
            return f"❌ File system error: {e}. Please check your storage configuration."
    except Exception as e:
        return f"❌ Unexpected error creating daily file: {e}. Please try again or contact support."


@tool
def add_timestamp_entry(content: str, target_date: str | None = None) -> str:
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
        return (
            "❌ Error: Cannot add empty journal entry. Please provide some content to write about."
        )

    try:
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                file_path = _add_timestamp_entry(content.strip(), parsed_date)
                return f"✅ Journal entry added to {file_path} with timestamp."
            except ValueError:
                return (
                    f"❌ Error: Invalid date format '{target_date}'. "
                    "Please use YYYY-MM-DD format (e.g., 2024-01-15)."
                )
        else:
            file_path = _add_timestamp_entry(content.strip())
            return f"✅ Journal entry added to today's file: {file_path}"

    except PermissionError as e:
        return (
            f"❌ Permission denied: {e}. "
            "Unable to write to journal file. Please check file permissions."
        )
    except OSError as e:
        if "space" in str(e).lower():
            return (
                f"❌ Insufficient disk space: {e}. "
                "Your entry has been saved, but storage is running low."
            )
        elif "read-only" in str(e).lower():
            return f"❌ File system is read-only: {e}. Cannot save journal entries."
        else:
            return f"❌ File system error: {e}. Entry may not have been saved properly."
    except Exception as e:
        return f"❌ Unexpected error adding entry: {e}. Please try again."


@tool
def save_journal_entry_with_summary(
    content: str, target_date: str | None = None, force_summary: bool = False
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
        return "❌ Error: Cannot save empty journal entry. Please write something to journal about."

    try:
        custom_date = None
        if target_date:
            try:
                custom_date = datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError:
                return (
                    f"❌ Error: Invalid date format '{target_date}'. "
                    "Please use YYYY-MM-DD format (e.g., 2024-01-15)."
                )

        result = _save_journal_entry_with_summary(
            content.strip(), custom_date=custom_date, force_summary=force_summary
        )
        return f"✅ {result}"

    except PermissionError as e:
        return (
            f"❌ Permission denied: {e}. "
            "Unable to save journal entry. Please check file permissions."
        )
    except OSError as e:
        if "space" in str(e).lower():
            # Try to save without summary as fallback
            try:
                file_path = _add_timestamp_entry(content.strip())
                return (
                    f"⚠️ Entry saved to {file_path} but summary failed due to "
                    "low disk space. Consider freeing up storage."
                )
            except Exception:
                return f"❌ Critical: Insufficient disk space and unable to save entry: {e}"
        elif "read-only" in str(e).lower():
            return f"❌ File system is read-only: {e}. Cannot save journal entries."
        else:
            # Try basic save as fallback
            try:
                file_path = _add_timestamp_entry(content.strip())
                return f"⚠️ Entry saved to {file_path} but with errors: {e}"
            except Exception:
                return f"❌ File system error prevented saving: {e}"
    except Exception as e:
        # Try basic save as last resort fallback
        try:
            file_path = _add_timestamp_entry(content.strip())
            return f"⚠️ Entry saved to {file_path} but summary generation failed: {e}"
        except Exception:
            return (
                f"❌ Failed to save journal entry: {e}. Please try again or use a simpler format."
            )


@tool
def search_by_date_range(start_date: str | None = None, end_date: str | None = None) -> str:
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

            return (
                f"📝 No journal entries found{date_info}. "
                "Try a different date range or create a new entry!"
            )

        # Format results
        result_lines = [f"📅 Found {len(results)} journal entries:"]
        for entry in results:
            word_info = f"({entry['word_count']} words)" if entry.get("word_count") else ""
            result_lines.append(f"• {entry['date']} - {entry['file_path']} {word_info}")
            if entry.get("mood"):
                result_lines.append(f"  💭 Mood: {entry['mood']}")
            if entry.get("topics"):
                result_lines.append(f"  🏷️ Topics: {', '.join(entry['topics'])}")

        return "\n".join(result_lines)

    except ValueError as e:
        if "date" in str(e).lower():
            return f"❌ Invalid date format: {e}. Please use YYYY-MM-DD format (e.g., 2024-01-15)."
        else:
            return f"❌ Invalid input: {e}"
    except OSError as e:
        if "permission" in str(e).lower() or "access" in str(e).lower():
            return f"❌ Cannot access journal files: {e}. Please check file permissions."
        else:
            return f"❌ File system error during search: {e}. Please try again."
    except Exception as e:
        return f"❌ Unexpected error during date search: {e}. Please try again or contact support."


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
    if not keywords or not keywords.strip():
        return "❌ Error: Please provide keywords to search for."

    try:
        keyword_list = keywords.strip().split()
        results = _search_by_keywords(
            keyword_list,
            case_sensitive=case_sensitive,
            search_content=search_content,
            search_frontmatter=search_frontmatter,
        )

        if not results:
            search_scope = []
            if search_content:
                search_scope.append("content")
            if search_frontmatter:
                search_scope.append("metadata")
            scope_text = " and ".join(search_scope) if search_scope else "files"

            return (
                f"🔍 No journal entries found containing keywords: '{keywords}' "
                f"in {scope_text}. Try different keywords or check spelling."
            )

        # Format results with scores
        result_lines = [f"🔍 Found {len(results)} entries matching '{keywords}':"]
        for entry in results:
            score = entry.get("match_score", 0)
            result_lines.append(f"• {entry['date']} - {entry['file_path']} (relevance: {score})")
            if entry.get("mood"):
                result_lines.append(f"  💭 Mood: {entry['mood']}")
            if entry.get("topics"):
                result_lines.append(f"  🏷️ Topics: {', '.join(entry['topics'])}")

        return "\n".join(result_lines)

    except OSError as e:
        if "permission" in str(e).lower() or "access" in str(e).lower():
            return f"❌ Cannot access journal files: {e}. Please check file permissions."
        else:
            return f"❌ File system error during keyword search: {e}. Please try again."
    except Exception as e:
        return f"❌ Unexpected error during keyword search: {e}. Please try again."


@tool
def search_by_mood(mood: str, exact_match: bool = False) -> str:
    """
    Search for journal entries by mood.

    Args:
        mood: The mood to search for (e.g., 'happy', 'sad', 'excited').
        exact_match: Whether to match the mood exactly or partially.

    Returns:
        str: Formatted search results.
    """
    if not mood or not mood.strip():
        return "❌ Error: Please specify a mood to search for (e.g., 'happy', 'sad', 'excited')."

    try:
        results = _search_by_mood(mood.strip(), exact_match=exact_match)

        if not results:
            match_type = "exactly" if exact_match else "containing"
            return (
                f"😐 No journal entries found with mood {match_type} '{mood}'. "
                "Try a different mood or use partial matching."
            )

        # Format results
        match_type = "exact" if exact_match else "partial"
        result_lines = [
            f"😊 Found {len(results)} entries with {match_type} mood match for '{mood}':"
        ]
        for entry in results:
            result_lines.append(f"• {entry['date']} - {entry['file_path']}")
            if entry.get("mood"):
                result_lines.append(f"  💭 Mood: {entry['mood']}")
            if entry.get("topics"):
                result_lines.append(f"  🏷️ Topics: {', '.join(entry['topics'])}")

        return "\n".join(result_lines)

    except OSError as e:
        if "permission" in str(e).lower() or "access" in str(e).lower():
            return f"❌ Cannot access journal files: {e}. Please check file permissions."
        else:
            return f"❌ File system error during mood search: {e}. Please try again."
    except Exception as e:
        return f"❌ Unexpected error during mood search: {e}. Please try again."


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
            result_lines.append(f"• {entry['date']} - {entry['file_path']} (score: {score})")
            result_lines.append(f"  Topics: {', '.join(entry.get('topics', []))}")
            if entry.get("mood"):
                result_lines.append(f"  Mood: {entry['mood']}")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Error searching by topics: {str(e)}"


@tool
def add_metadata_to_entry(
    file_path: str,
    mood: str | None = None,
    keywords: str | None = None,
    topics: str | None = None,
    tags: str | None = None,
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
        kwargs: dict[str, Any] = {}
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
    prompt=f"""Today is {current_date}. You are Luna, a thoughtful and empathetic daily \
journaling assistant designed to help users reflect deeply on their experiences and capture \
meaningful insights.

## 🌟 Your Personality & Approach

You are a warm, supportive companion who feels like talking to a trusted friend who genuinely \
cares about personal growth. You:

- **Listen actively** and respond with genuine curiosity and empathy
- **Ask thoughtful questions** that help users discover insights they might not have noticed
- **Celebrate progress** and acknowledge both challenges and victories, no matter how small
- **Respect boundaries** and never push when someone seems ready to finish
- **Stay curious** about what matters most to each person's unique journey

## 📝 Journaling Workflow & Instructions

### **Session Flow:**
1. **Welcome & Check-in**: Start each session with a warm greeting and open-ended question \
about their day
2. **Active Listening**: Respond to what they share with empathy and follow-up questions \
(max 2 questions)
3. **Guided Reflection**: Use CBT-style questions to encourage deeper thinking
4. **Graceful Completion**: Detect completion signals and save their reflections
5. **Confirmation**: Provide encouraging closure with next steps

### **Your Conversation Tools:**
- Use `save_journal_entry_with_summary` when they're done sharing (handles summarization \
automatically)
- Use `search_by_*` tools to help them find patterns in past entries
- Use `add_metadata_to_entry` to tag entries with mood, topics, or keywords
- Use `create_daily_file` if they want to start fresh for a specific date

### **Question Types to Explore:**
- **Emotions**: "What emotions came up for you?" "How are you feeling right now?"
- **Growth**: "What did this teach you?" "How did you handle this differently than before?"
- **Priorities**: "What mattered most to you today?" "What deserves more attention?"
- **Insights**: "What would you want to remember from this?" "What patterns do you notice?"
- **Forward-looking**: "What would tomorrow-you thank today-you for doing?"

## 🔍 Search & Reflection Capabilities

Help users connect current experiences with past insights:
- Find similar situations they've navigated before
- Surface patterns in their emotional responses or growth
- Celebrate progress by showing how far they've come
- Suggest topics or themes worth exploring further

## 💡 Key Guidelines

**Conversation Flow:**
- Ask 1-2 thoughtful follow-up questions maximum per response
- Watch for completion signals: "I'm done", "finished", "that's all", or empty responses
- Let natural pauses happen - don't feel pressure to always ask more

**Tone & Language:**
- Use warm, conversational language (not clinical or formal)
- Acknowledge their feelings without trying to "fix" everything
- Ask permission before diving deeper: "Would you like to explore that more?"
- Use their own words and language patterns when reflecting back

**Practical Actions:**
- Always save completed entries using the appropriate tools
- Suggest adding metadata (mood, topics) if it feels natural
- Offer to search past entries when relevant patterns emerge
- Keep entries organized and easily searchable

## 🌱 Remember

You're not just collecting text - you're facilitating self-discovery. Every interaction should \
leave them feeling heard, understood, and maybe just a little more aware of their own wisdom.

When they finish sharing, save their complete reflection and offer genuine encouragement about \
their commitment to self-reflection.""",
)
