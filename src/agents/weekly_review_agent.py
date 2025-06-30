import logging
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from src.tools.todoist_tools import get_completed_tasks, get_all_tasks
from src.tools.calendar_tools import (
    get_past_week_accomplishments as get_calendar_accomplishments,
)
from src.tools.journal_tools import search_by_keywords, search_by_mood, search_by_topics

# Configure logging
logger = logging.getLogger(__name__)

# Session management and context tools for memory handling


@tool
def start_weekly_review_session(
    session_type: str = "full", focus_areas: str = ""
) -> str:
    """
    Initialize a new weekly review session with context tracking.

    Args:
        session_type: Type of review - "full", "quick", or "focused" (default: "full")
        focus_areas: Specific areas to focus on, comma-separated (optional)

    Returns:
        str: Session initialization confirmation with guidance
    """
    session_types = {
        "full": "Complete 6-step GTD weekly review (45-60 minutes)",
        "quick": "Abbreviated review focusing on key priorities (15-20 minutes)",
        "focused": "Targeted review of specific areas (20-30 minutes)",
    }

    session_desc = session_types.get(session_type, session_types["full"])

    context_msg = "🎯 **Weekly Review Session Started**\n\n"
    context_msg += f"**Session Type:** {session_desc}\n\n"

    if focus_areas:
        context_msg += f"**Focus Areas:** {focus_areas}\n\n"

    context_msg += (
        "I'll guide you through your weekly review step by step. "
        "We can adjust the pace and depth based on your available time and energy. "
        "Let's start by checking in - how are you feeling right now, and how much "
        "time do you have available?"
    )

    return context_msg


@tool
def track_review_progress(
    completed_steps: str, current_step: str = "", notes: str = ""
) -> str:
    """
    Track progress through the weekly review process for context continuity.

    Args:
        completed_steps: Comma-separated list of completed steps (e.g., "clear,current")
        current_step: Current step being worked on (optional)
        notes: Any session notes or insights to remember (optional)

    Returns:
        str: Progress summary and next step guidance
    """
    step_names = {
        "clear": "✅ Get Clear (Mind Sweep & Collection)",
        "current": "✅ Get Current (Review Past Week)",
        "creative": "✅ Get Creative (Areas of Responsibility)",
        "projects": "✅ Review Projects List",
        "actions": "✅ Review Next Actions Lists",
        "calendar": "✅ Review Calendar & Plan Ahead",
    }

    completed_list = [
        step.strip() for step in completed_steps.split(",") if step.strip()
    ]

    progress_msg = "📋 **Weekly Review Progress**\n\n"

    for step in completed_list:
        if step in step_names:
            progress_msg += f"{step_names[step]}\n"

    if current_step and current_step in step_names:
        current_desc = step_names[current_step].replace("✅", "Working on")
        progress_msg += f"🔄 Currently: {current_desc}\n"

    # Determine next step
    all_steps = ["clear", "current", "creative", "projects", "actions", "calendar"]
    next_steps = [step for step in all_steps if step not in completed_list]

    if next_steps:
        next_step = next_steps[0]
        next_desc = step_names[next_step].replace("✅", "Next -")
        progress_msg += f"\n🎯 **Next:** {next_desc}"
    else:
        progress_msg += "\n🎉 **Weekly Review Complete!** Ready to save and wrap up."

    if notes:
        progress_msg += f"\n\n📝 **Session Notes:** {notes}"

    return progress_msg


@tool
def manage_review_context(
    action: str, key: str = "", value: str = "", context_type: str = "session"
) -> str:
    """
    Manage context and state during the weekly review for better continuity.

    Args:
        action: Action to perform - "set", "get", "list", or "clear"
        key: Context key to set/get (for set/get actions)
        value: Context value to store (for set action)
        context_type: Type of context - "session", "insights", "commitments" (default: "session")

    Returns:
        str: Context operation result
    """
    # This is a placeholder implementation - in a real system this would integrate
    # with the LangGraph memory/store systems

    if action == "set" and key and value:
        return f"📝 Context stored: {context_type}.{key} = {value}"
    elif action == "get" and key:
        return (
            f"📖 Retrieved context: {context_type}.{key} "
            "(placeholder - would retrieve stored value)"
        )
    elif action == "list":
        return (
            f"📋 Available {context_type} context keys: "
            "(placeholder - would list actual keys)"
        )
    elif action == "clear":
        return f"🗑️ Cleared {context_type} context"
    else:
        return "❌ Invalid context action. Use: set, get, list, or clear"


@tool
def save_review_insights(
    insights: str, commitments: str = "", reflection: str = ""
) -> str:
    """
    Save key insights and commitments from the weekly review session.

    Args:
        insights: Key insights and patterns discovered during review
        commitments: Specific commitments made for the upcoming week
        reflection: Overall reflection on the review process

    Returns:
        str: Confirmation of saved insights with summary
    """
    current_date = datetime.now().strftime("%Y-%m-%d")

    summary = f"💡 **Weekly Review Insights Saved** (Week ending {current_date})\n\n"

    if insights:
        summary += f"**Key Insights:**\n{insights}\n\n"

    if commitments:
        summary += f"**Commitments for Next Week:**\n{commitments}\n\n"

    if reflection:
        summary += f"**Process Reflection:**\n{reflection}\n\n"

    summary += (
        "These insights will be available for reference in future weekly reviews "
        "to track progress and patterns."
    )

    return summary


# Placeholder tools for weekly review functionality
# These will be expanded in later tasks


@tool
def get_past_week_accomplishments(
    user_id: str, start_date: str | None = None, end_date: str | None = None
) -> str:
    """
    Analyze accomplishments from the past week using task and calendar data.

    Args:
        user_id: User identifier for authentication
        start_date: Start date in YYYY-MM-DD format (optional, defaults to week start)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)

    Returns:
        str: Summary of past week accomplishments
    """
    try:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        if start_date:
            week_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            week_end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Fetch completed tasks from Todoist
        completed = get_completed_tasks(
            user_id, since=week_start, until=week_end, limit=100
        )
        completed_tasks = completed.get("items", [])

        # Fetch calendar accomplishments - pass user_id for authentication
        try:
            # Create calendar fetcher with user context
            from src.tools.calendar_tools import CalendarDataFetcher, CalendarAnalyzer
            fetcher = CalendarDataFetcher()
            analyzer = CalendarAnalyzer()
            
            # Get events from past week
            calendar_events = []
            week_start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
            week_end_dt = datetime.combine(week_end, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            # Get all calendar events for this user's accounts
            accounts = fetcher.get_all_google_accounts()
            user_accounts = [acc for acc in accounts if acc['user_id'] == user_id and acc['is_valid']]
            
            if user_accounts:
                for account in user_accounts:
                    calendars = fetcher.get_calendars_for_account(account['user_id'])
                    for calendar in calendars:
                        events = fetcher.fetch_events_from_calendar(
                            account['user_id'], 
                            calendar.get('id'), 
                            week_start_dt, 
                            week_end_dt
                        )
                        calendar_events.extend(events)
                
                # Filter to accomplishments
                calendar_events = analyzer.get_past_week_accomplishments(calendar_events)
            
        except Exception as e:
            logger.warning(f"Error fetching calendar accomplishments: {e}")
            calendar_events = []

        output = f"## 🏆 Past Week Accomplishments ({week_start} to {week_end})\n\n"
        output += "### ✅ Completed Tasks (Todoist)\n"
        if completed_tasks:
            for task in completed_tasks:
                content = task.get("content") or task.get("title") or "Untitled Task"
                project = task.get("project_id", "")
                output += f"- {content} (Project: {project})\n"
        else:
            output += "No completed tasks found for this week.\n"

        output += "\n### 📅 Calendar Accomplishments\n"
        if calendar_events:
            for event in calendar_events:
                summary = (
                    getattr(event, "summary", None)
                    or getattr(event, "title", None)
                    or "Untitled Event"
                )
                start = getattr(event, "start_time", None)
                if start:
                    start_str = start.strftime("%Y-%m-%d %H:%M")
                    output += f"- {summary} ({start_str})\n"
                else:
                    output += f"- {summary}\n"
        else:
            output += "No calendar accomplishments found for this week.\n"

        return output
    except Exception as e:
        return (
            "📅 Past week accomplishments analysis placeholder. "
            "This will integrate with Todoist and Calendar APIs.\n"
            f"Error: {e}"
        )


def _get_previous_weekly_reviews_mock(user_id: str, num_reviews: int = 3):
    """
    Placeholder for fetching previous weekly reviews from storage.
    TODO: Replace with real storage integration when available.
    """
    # Example mock data structure
    return [
        {
            "week": "2024-06-07",
            "incomplete_tasks": [
                {"id": "123", "content": "Finish project report", "project_id": "A"},
                {"id": "124", "content": "Email client", "project_id": "B"},
            ],
        },
        {
            "week": "2024-05-31",
            "incomplete_tasks": [
                {"id": "123", "content": "Finish project report", "project_id": "A"},
                {"id": "125", "content": "Book dentist appointment", "project_id": "C"},
            ],
        },
    ]


@tool
def analyze_incomplete_tasks(user_id: str) -> str:
    """
    Identify tasks that are incomplete or stalled from previous reviews by comparing current incomplete tasks to those from previous weeks.

    Args:
        user_id: User identifier for authentication

    Returns:
        str: Analysis of incomplete and stalled tasks
    """
    # Fetch all current incomplete tasks
    try:
        current_tasks = get_all_tasks(user_id)
    except Exception as e:
        return f"❌ Error fetching current tasks: {e}"
    current_task_ids = {task["id"] for task in current_tasks}
    # Fetch previous weekly reviews (placeholder)
    previous_reviews = _get_previous_weekly_reviews_mock(user_id)
    # Collect tasks that have appeared as incomplete in previous reviews and are still incomplete
    stalled_tasks = []
    for review in previous_reviews:
        for task in review.get("incomplete_tasks", []):
            if task["id"] in current_task_ids:
                stalled_tasks.append(task)
    # Remove duplicates
    seen = set()
    unique_stalled_tasks = []
    for task in stalled_tasks:
        if task["id"] not in seen:
            unique_stalled_tasks.append(task)
            seen.add(task["id"])
    # Format output
    output = "## ⏸️ Stalled/Uncompleted Tasks\n\n"
    if unique_stalled_tasks:
        for task in unique_stalled_tasks:
            output += f"- {task['content']} (Project: {task.get('project_id', '')})\n"
        output += "\nThese tasks have remained incomplete across multiple reviews. Consider prioritizing or re-evaluating them.\n"
    else:
        output += "No stalled or repeatedly uncompleted tasks detected from previous reviews.\n"
    output += "\n*Note: Previous review data is currently a placeholder. This will use real storage integration in the future.*\n"
    return output


@tool
def identify_upcoming_priorities(weeks_ahead: int = 1) -> str:
    """
    Identify high-priority tasks and commitments for the upcoming period.

    Args:
        weeks_ahead: Number of weeks to look ahead (default: 1)

    Returns:
        str: Analysis of upcoming priorities and scheduling recommendations
    """
    # Placeholder implementation
    return (
        f"🎯 Upcoming priorities analysis placeholder for {weeks_ahead} week(s). "
        "This will integrate with calendar availability and task deadlines."
    )


@tool
def save_weekly_review_session(review_data: str, week_ending: str | None = None) -> str:
    """
    Save the completed weekly review session to database.

    Args:
        review_data: Complete weekly review content in markdown format
        week_ending: Week ending date in YYYY-MM-DD format (optional, defaults to today)

    Returns:
        str: Confirmation of saved review
    """
    # Placeholder implementation
    current_date = datetime.now().strftime("%Y-%m-%d")
    week_date = week_ending or current_date
    return (
        f"✅ Weekly review saved for week ending {week_date}. "
        "Database storage will be implemented in later tasks."
    )


@tool
def get_previous_weekly_reviews(num_reviews: int = 3) -> str:
    """
    Retrieve previous weekly reviews for continuity and pattern analysis.

    Args:
        num_reviews: Number of previous reviews to retrieve (default: 3)

    Returns:
        str: Summary of previous weekly reviews
    """
    # Placeholder implementation
    return (
        f"📚 Previous {num_reviews} weekly reviews placeholder. "
        "This will provide historical context and pattern detection."
    )


@tool
def assess_data_availability(data_sources: str = "tasks,calendar,journal") -> str:
    """
    Assess what data is available for the weekly review and identify gaps.

    Args:
        data_sources: Comma-separated list of data sources to check (default: "tasks,calendar,journal")

    Returns:
        str: Assessment of available data and recommendations for sparse scenarios
    """
    # This is a placeholder - in real implementation would check actual integrations
    sources = [source.strip() for source in data_sources.split(",")]

    assessment = "📊 **Data Availability Assessment**\n\n"

    # Simulate data availability check
    mock_availability = {
        "tasks": "limited",  # Could be: "available", "limited", "missing"
        "calendar": "missing",
        "journal": "available",
    }

    available_sources = []
    limited_sources = []
    missing_sources = []

    for source in sources:
        status = mock_availability.get(source, "missing")
        if status == "available":
            available_sources.append(source)
        elif status == "limited":
            limited_sources.append(source)
        else:
            missing_sources.append(source)

    if available_sources:
        assessment += f"✅ **Available:** {', '.join(available_sources)}\n"
    if limited_sources:
        assessment += f"⚠️ **Limited:** {', '.join(limited_sources)}\n"
    if missing_sources:
        assessment += f"❌ **Missing:** {', '.join(missing_sources)}\n"

    assessment += "\n**Recommendations:**\n"

    if len(missing_sources) >= 2:
        assessment += "• Consider a **manual-guided review** focusing on reflection and planning\n"
        assessment += (
            "• Use memory and observation to reconstruct the week's key events\n"
        )

    if "tasks" in missing_sources:
        assessment += (
            "• We'll rely on manual task recall and focus on future planning\n"
        )

    if "calendar" in missing_sources:
        assessment += (
            "• Manual time reflection will help identify patterns and commitments\n"
        )

    assessment += (
        "• This review will help establish better data habits for future weeks\n"
    )

    return assessment


@tool
def guide_manual_weekly_reflection(focus_area: str = "general") -> str:
    """
    Provide guided questions for manual weekly reflection when data is sparse.

    Args:
        focus_area: Area to focus on - "general", "accomplishments", "challenges", "planning"

    Returns:
        str: Structured reflection questions and prompts
    """
    reflection_guides = {
        "general": {
            "title": "General Weekly Reflection",
            "questions": [
                "What were the 3 most significant things you accomplished this week?",
                "What challenges or obstacles did you face?",
                "What patterns did you notice in your energy, focus, or productivity?",
                "What would you do differently if you could repeat this week?",
                "What are you most grateful for from this week?",
            ],
        },
        "accomplishments": {
            "title": "Accomplishments & Progress Review",
            "questions": [
                "What projects or tasks did you complete this week?",
                "What progress did you make on ongoing initiatives?",
                "Which accomplishments felt most meaningful or impactful?",
                "What skills did you develop or strengthen?",
                "What positive feedback or recognition did you receive?",
            ],
        },
        "challenges": {
            "title": "Challenges & Learning Review",
            "questions": [
                "What obstacles or setbacks did you encounter?",
                "Which tasks or projects got stalled, and why?",
                "What patterns of procrastination or avoidance did you notice?",
                "What external factors impacted your week (interruptions, changes)?",
                "What would help you handle similar challenges better next time?",
            ],
        },
        "planning": {
            "title": "Forward Planning & Priorities",
            "questions": [
                "What are your top 3 priorities for next week?",
                "What commitments or deadlines are coming up?",
                "What would make next week feel successful?",
                "What do you need to say 'no' to in order to focus on what matters?",
                "What support or resources would help you succeed next week?",
            ],
        },
    }

    guide = reflection_guides.get(focus_area, reflection_guides["general"])

    output = f"🤔 **{guide['title']}**\n\n"
    output += "Take your time with these questions. Even without detailed data, "
    output += "your reflection and memory can provide valuable insights:\n\n"

    for i, question in enumerate(guide["questions"], 1):
        output += f"{i}. {question}\n"

    output += "\nFeel free to elaborate on any that resonate with you. "
    output += "We can dive deeper into specific areas that seem important."

    return output


@tool
def suggest_data_improvement_strategies() -> str:
    """
    Provide recommendations for improving data availability for future weekly reviews.

    Returns:
        str: Actionable strategies for better data capture and integration
    """
    strategies = """🔧 **Improving Data for Future Weekly Reviews**

To make your future weekly reviews more insightful and efficient, consider these strategies:

## 📋 Task & Project Tracking
• **Digital Task Management**: Set up Todoist, Things, or another task manager
• **Capture Everything**: Use inbox systems to collect all commitments and ideas
• **Daily Reviews**: Spend 5 minutes each evening updating task status
• **Project Definition**: Clearly define multi-step projects vs. single actions

## 📅 Calendar Integration
• **Time Blocking**: Schedule focused work time, not just meetings
• **Activity Logging**: Note what you actually worked on during blocked time
• **Weekly Templates**: Create recurring time blocks for important activities
• **Reflection Time**: Schedule weekly review time as a recurring appointment

## 📝 Simple Tracking Methods
• **Daily Notes**: Keep brief daily notes of key accomplishments and challenges
• **Weekly Themes**: Track focus areas or major projects each week
• **Energy Patterns**: Note when you feel most/least productive
• **Weekly Questions**: Answer 2-3 consistent questions each week

## 🔄 Habit Building
• **Start Small**: Pick one tracking method and use it consistently for 2 weeks
• **Review Effectiveness**: During weekly reviews, assess what data was most helpful
• **Adjust Systems**: Modify tracking based on what provides real insight
• **Integration Focus**: Connect systems so data flows automatically where possible

## 💡 Quick Wins
• **Phone Notes**: Use voice memos or quick notes throughout the week
• **Photo Documentation**: Take photos of handwritten notes or whiteboard sessions
• **Email to Self**: Send yourself quick updates about progress or insights
• **End-of-Day Ritual**: Spend 2 minutes noting the day's key outcomes

Remember: The goal is insight, not perfection. Start with whatever feels manageable and build from there."""

    return strategies


@tool
def adapt_review_for_sparse_data(
    available_data: str = "", session_type: str = "adaptive"
) -> str:
    """
    Adapt the weekly review process based on available data and constraints.

    Args:
        available_data: Description of what data is available (optional)
        session_type: Type of adapted session - "adaptive", "minimal", "planning-focused"

    Returns:
        str: Customized review approach and modified process
    """
    adaptations = {
        "adaptive": {
            "title": "Adaptive Weekly Review",
            "description": "Flexible approach that works with whatever data you have",
            "process": [
                "🧠 **Mind Sweep**: Start with what you remember from the week",
                "🔄 **Present State**: Assess current projects and commitments",
                "🎯 **Priority Focus**: Identify what matters most right now",
                "📋 **Next Actions**: Define clear next steps for key areas",
                "🚀 **Week Ahead**: Plan priorities with realistic expectations",
            ],
        },
        "minimal": {
            "title": "Minimal Weekly Review",
            "description": "Streamlined 15-minute review focusing on essentials",
            "process": [
                "⚡ **Quick Wins**: What went well this week?",
                "🎯 **Key Priority**: What's the #1 focus for next week?",
                "🚧 **Obstacle Check**: What might get in the way?",
                "✅ **One Commitment**: Make one clear commitment for next week",
            ],
        },
        "planning-focused": {
            "title": "Forward-Planning Review",
            "description": "Focus on upcoming week when past data is limited",
            "process": [
                "📅 **Calendar Scan**: Review upcoming commitments and deadlines",
                "🎯 **Outcome Definition**: What would make next week successful?",
                "⚖️ **Capacity Check**: Realistic assessment of available time/energy",
                "🛡️ **Protection Plan**: How to guard your most important work",
                "🔄 **Flexibility Buffer**: Plan for the unexpected",
            ],
        },
    }

    adaptation = adaptations.get(session_type, adaptations["adaptive"])

    output = f"🔧 **{adaptation['title']}**\n\n"
    output += f"{adaptation['description']}\n\n"

    if available_data:
        output += f"**Available Data:** {available_data}\n\n"

    output += "**Adapted Process:**\n"
    for step in adaptation["process"]:
        output += f"• {step}\n"

    output += (
        "\nThis approach focuses on what you can control and influence, "
        "using reflection and planning to create value even with limited historical data."
    )

    return output


@tool
def review_areas_of_responsibility_and_projects() -> str:
    """
    Guide the user through reviewing each area of responsibility and their active projects.

    Returns:
        str: Structured markdown summary of areas and projects review
    """
    professional_areas = [
        ("Career/Professional Development", "advancement, skills, networking"),
        ("Job Responsibilities", "primary work duties and projects"),
        ("Team/Staff Management", "if managing others"),
        ("Financial Management", "budgets, investments, financial goals"),
        ("Business Development", "if entrepreneur or business owner"),
    ]
    personal_areas = [
        ("Home & Property", "maintenance, organization, living environment"),
        ("Family & Relationships", "spouse, children, extended family, friends"),
        ("Health & Fitness", "physical health, exercise, nutrition, wellness"),
        ("Personal Development", "learning, growth, hobbies, interests"),
        ("Community & Service", "volunteering, civic engagement, giving back"),
        ("Life Goals & Values", "purpose, spirituality, long-term vision"),
    ]

    output = "## 🗂️ Areas of Responsibility & Project Review\n\n"
    output += "### Professional Areas\n"
    for area, desc in professional_areas:
        output += f"- **{area}** ({desc})\n"
        output += "    - Are you giving this area enough attention?\n"
        output += "    - List active projects in this area.\n"
        output += "    - For each project: Is it active, stalled, completed, or new?\n"
        output += "    - Any new projects or adjustments needed?\n"
    output += "\n### Personal Areas\n"
    for area, desc in personal_areas:
        output += f"- **{area}** ({desc})\n"
        output += "    - Are you giving this area enough attention?\n"
        output += "    - List active projects in this area.\n"
        output += "    - For each project: Is it active, stalled, completed, or new?\n"
        output += "    - Any new projects or adjustments needed?\n"
    output += "\nPlease provide your responses for each area. We'll summarize and update your project list accordingly.\n"
    return output


@tool
def detect_recurring_themes_and_stressors(
    weeks: int = 4,
    stressor_keywords: list[str] = [
        "stress",
        "overwhelm",
        "anxiety",
        "blocked",
        "frustration",
        "tired",
        "burnout",
        "conflict",
        "worry",
        "deadline",
        "pressure",
        "problem",
        "issue",
        "challenge",
        "difficult",
        "delay",
        "stuck",
    ],
) -> str:
    """
    Detect recurring themes and stressors from the past N weeks of journal entries and calendar events.

    Args:
        weeks: Number of weeks to look back (default: 4)
        stressor_keywords: List of keywords to identify stressors

    Returns:
        str: Markdown summary of recurring themes and stressors
    """
    from datetime import date, timedelta

    today = date.today()
    start_date = today - timedelta(days=7 * weeks)
    # Search journal entries for recurring keywords, moods, and topics
    # For simplicity, use a fixed set of common theme keywords
    theme_keywords = [
        "progress",
        "success",
        "growth",
        "learning",
        "family",
        "work",
        "project",
        "goal",
        "health",
        "energy",
        "focus",
        "motivation",
        "relationship",
        "gratitude",
        "win",
        "milestone",
        "habit",
        "routine",
        "reflection",
        "achievement",
    ]
    # Find recurring themes
    theme_counts = {}
    for keyword in theme_keywords:
        results = search_by_keywords(
            keyword, search_content=True, search_frontmatter=True
        )
        count = sum(
            1
            for r in results
            if r.get("date")
            and start_date.strftime("%Y-%m-%d")
            <= r["date"]
            <= today.strftime("%Y-%m-%d")
        )
        if count > 0:
            theme_counts[keyword] = count
    # Find recurring stressors
    stressor_counts = {}
    for keyword in stressor_keywords:
        results = search_by_keywords(
            keyword, search_content=True, search_frontmatter=True
        )
        count = sum(
            1
            for r in results
            if r.get("date")
            and start_date.strftime("%Y-%m-%d")
            <= r["date"]
            <= today.strftime("%Y-%m-%d")
        )
        if count > 0:
            stressor_counts[keyword] = count
    # Find most common moods
    mood_list = [
        "stressed",
        "anxious",
        "tired",
        "overwhelmed",
        "happy",
        "grateful",
        "productive",
        "motivated",
        "calm",
        "excited",
    ]
    mood_counts = {}
    for mood in mood_list:
        results = search_by_mood(mood)
        count = sum(
            1
            for r in results
            if r.get("date")
            and start_date.strftime("%Y-%m-%d")
            <= r["date"]
            <= today.strftime("%Y-%m-%d")
        )
        if count > 0:
            mood_counts[mood] = count
    # Find most common topics
    topic_list = [
        "work",
        "family",
        "health",
        "project",
        "goal",
        "relationship",
        "stress",
        "energy",
        "habit",
        "routine",
    ]
    topic_counts = {}
    for topic in topic_list:
        results = search_by_topics(topic)
        count = sum(
            1
            for r in results
            if r.get("date")
            and start_date.strftime("%Y-%m-%d")
            <= r["date"]
            <= today.strftime("%Y-%m-%d")
        )
        if count > 0:
            topic_counts[topic] = count
    # Format summary
    output = f"## 🔁 Recurring Themes and Stressors (Last {weeks} Weeks)\n\n"
    output += "### 🌱 Recurring Themes\n"
    if theme_counts:
        for k, v in sorted(theme_counts.items(), key=lambda x: -x[1]):
            output += f"- {k} ({v} mentions)\n"
    else:
        output += "No strong recurring themes detected.\n"
    output += "\n### ⚠️ Recurring Stressors\n"
    if stressor_counts or any(
        m in mood_counts for m in ["stressed", "anxious", "tired", "overwhelmed"]
    ):
        for k, v in sorted(stressor_counts.items(), key=lambda x: -x[1]):
            output += f"- {k} ({v} mentions)\n"
        for m in ["stressed", "anxious", "tired", "overwhelmed"]:
            if m in mood_counts:
                output += f"- Mood: {m} ({mood_counts[m]} entries)\n"
    else:
        output += "No strong recurring stressors detected.\n"
    output += "\n### 🏷️ Common Topics\n"
    if topic_counts:
        for k, v in sorted(topic_counts.items(), key=lambda x: -x[1]):
            output += f"- {k} ({v} entries)\n"
    else:
        output += "No dominant topics found.\n"
    return output


# Configure tools for the weekly review agent including session management
tools = [
    # Session management and context tools
    start_weekly_review_session,
    track_review_progress,
    manage_review_context,
    save_review_insights,
    # Core weekly review functionality
    get_past_week_accomplishments,
    analyze_incomplete_tasks,
    identify_upcoming_priorities,
    save_weekly_review_session,
    get_previous_weekly_reviews,
    assess_data_availability,
    guide_manual_weekly_reflection,
    suggest_data_improvement_strategies,
    adapt_review_for_sparse_data,
    review_areas_of_responsibility_and_projects,
    detect_recurring_themes_and_stressors,
]

current_date = datetime.now().strftime("%Y-%m-%d")

# Create the agent with memory and context handling
weekly_review_agent = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=tools,
    prompt=f"""Today is {current_date}. You are a Weekly Review and Planning Assistant \
designed to help users conduct thorough GTD-style weekly reviews following David \
Allen's Getting Things Done methodology.

## 🎯 GTD Weekly Review Purpose

The Weekly Review is the heart of the GTD system - a time to regain control and \
perspective, ensuring your system is current and your mind is clear. You help users \
achieve "mind like water" by systematically reviewing all commitments and projects.

## 🧠 Memory & Context Management

You have access to session management tools to maintain context throughout the review:
- **start_weekly_review_session**: Initialize sessions with proper context
- **track_review_progress**: Keep track of completed steps and current position
- **manage_review_context**: Store and retrieve important session information
- **save_review_insights**: Capture key insights and commitments

Use these tools to:
- Remember what's been covered and what's next
- Maintain continuity if the session is interrupted
- Track insights and patterns across the conversation
- Ensure nothing important is lost

## 🔍 Sparse Data Handling (FR-027)

You have tools to gracefully handle scenarios with limited data:
- **assess_data_availability**: Check what data sources are available
- **guide_manual_weekly_reflection**: Provide structured reflection questions
- **suggest_data_improvement_strategies**: Help users build better data habits
- **adapt_review_for_sparse_data**: Modify the review process for available data

**When data is sparse:**
- Start with `assess_data_availability` to understand limitations
- Use `adapt_review_for_sparse_data` to choose appropriate approach
- Leverage manual reflection tools to extract insights from memory
- Focus on forward planning when historical data is limited
- Suggest improvements for future reviews without being pushy

**Adaptive Approaches:**
- **Full Data**: Complete 6-step GTD process with integrated insights
- **Limited Data**: Focus on available sources, supplement with reflection
- **Minimal Data**: Streamlined review emphasizing planning and priorities
- **No External Data**: Manual reflection and forward-focused planning

## 📋 GTD Weekly Review Process

Follow David Allen's proven 6-step weekly review process:

### **Step 1: Get Clear (Mind Sweep & Collection)**
- Review previous weekly review notes and any loose ends
- Collect and process any new items that have come up
- Empty all inboxes (physical, digital, mental)
- Ensure all open loops are captured in trusted system

### **Step 2: Get Current (Review Past Week)**
- Use tools to analyze what was accomplished from tasks and calendar
- Review completed projects and next actions from past week
- Identify what worked well and what could be improved
- Process any notes or insights from daily reviews

### **Step 3: Get Creative (Areas of Responsibility Review)**
Guide review of all Areas of Responsibility using GTD framework:

**Professional Areas:**
- 📊 **Career/Professional Development** - advancement, skills, networking
- 💼 **Job Responsibilities** - primary work duties and projects
- 👥 **Team/Staff Management** - if managing others
- 💰 **Financial Management** - budgets, investments, financial goals
- 🏢 **Business Development** - if entrepreneur or business owner

**Personal Areas:**
- 🏠 **Home & Property** - maintenance, organization, living environment
- 👨‍👩‍👧‍👦 **Family & Relationships** - spouse, children, extended family, friends
- 💪 **Health & Fitness** - physical health, exercise, nutrition, wellness
- 🧠 **Personal Development** - learning, growth, hobbies, interests
- 🤝 **Community & Service** - volunteering, civic engagement, giving back
- 🎯 **Life Goals & Values** - purpose, spirituality, long-term vision

**For each area, ask:**
- Is this area getting appropriate attention?
- Are there any new projects or commitments needed?
- What's working well, what needs adjustment?
- Any someday/maybe items to capture?

### **Step 4: Review Projects List**
- Review all active projects for completeness and currency
- Ensure each project has a clear outcome and next action
- Move completed projects to "done" status
- Identify any stalled projects and determine why
- Add any new projects that emerged from areas review

### **Step 5: Review Next Actions Lists**
- Check all context-based action lists (@calls, @computer, @errands, etc.)
- Remove completed actions
- Ensure actions are current and relevant
- Add new next actions for active projects
- Review waiting-for list and follow up as needed

### **Step 6: Review Calendar & Plan Ahead**
- Review past week's calendar for insights and follow-ups
- Look ahead at upcoming commitments and deadlines
- Identify upcoming priorities and time-sensitive items
- Block time for important but not urgent work
- Ensure realistic expectations for upcoming week's capacity

## 🔧 Your GTD Tools & Capabilities

- **get_past_week_accomplishments**: Review completed tasks and calendar events
- **analyze_incomplete_tasks**: Identify stalled projects and next actions
- **identify_upcoming_priorities**: Surface time-sensitive and important commitments
- **save_weekly_review_session**: Capture complete review in trusted system
- **get_previous_weekly_reviews**: Maintain consistency and track progress

## 💡 GTD Principles to Maintain

**Capture Everything:**
- Help identify any uncommitted items or open loops
- Ensure all thoughts and commitments are in trusted system
- Nothing should remain "in their head"

**Clarify Meaning:**
- For each item: Is it actionable? What's the desired outcome?
- Define clear next actions - physical, visible activities
- Distinguish between projects (multi-step outcomes) and single actions

**Organize by Context:**
- Group actions by where/when they can be done
- Maintain clean boundaries between different lists
- Keep reference material separate from actionable items

**Regular Review:**
- Weekly review is sacred time for maintaining system integrity
- Daily reviews keep system current between weekly reviews
- Monthly/quarterly reviews for higher-level perspective

**Engage with Confidence:**
- Decisions about what to do moment-to-moment should feel trusted
- System should support intuitive choices about priorities
- Goal is "mind like water" - clear, focused, and responsive

## 🌟 GTD Weekly Review Outcomes

By the end of each session, users should feel:
- **Clear** - mind empty of open loops and uncommitted items
- **Current** - system updated with latest realities and commitments
- **Creative** - perspective on broader goals and possibilities
- **Confident** - trust in their system and next actions
- **Capable** - realistic about what they can accomplish

## 💬 Conversational Guidelines

**Session Management:**
- Start each session by using `start_weekly_review_session` to set context
- Use `track_review_progress` regularly to maintain continuity
- Store important insights with `manage_review_context` as they emerge
- Save key outcomes with `save_review_insights` before concluding

**Memory & Continuity:**
- Remember what's been discussed and where you are in the process
- Reference previous points and build on earlier insights
- If the conversation gets interrupted, quickly recap where you were
- Connect current insights to patterns from past reviews

**Adaptive Approach:**
- Adjust depth and pace based on available time and energy
- Offer different session types (full, quick, focused) as appropriate
- Be flexible about order if certain areas need more attention
- Gracefully handle incomplete sessions with clear next steps

Guide them through this sacred time with patience, ensuring thoroughness without \
overwhelm. The Weekly Review is their weekly appointment with themselves to regain \
control and perspective.""",
)
