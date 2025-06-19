from datetime import datetime

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


# Placeholder tools for weekly review functionality
# These will be expanded in later tasks


@tool
def get_past_week_accomplishments(
    start_date: str | None = None, end_date: str | None = None
) -> str:
    """
    Analyze accomplishments from the past week using task and calendar data.

    Args:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to week start)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)

    Returns:
        str: Summary of past week accomplishments
    """
    # Placeholder implementation
    return (
        "📅 Past week accomplishments analysis placeholder. "
        "This will integrate with Todoist and Calendar APIs."
    )


@tool
def analyze_incomplete_tasks() -> str:
    """
    Identify tasks that are incomplete or stalled from previous reviews.

    Returns:
        str: Analysis of incomplete and stalled tasks
    """
    # Placeholder implementation
    return (
        "📋 Incomplete tasks analysis placeholder. "
        "This will analyze Todoist task status and patterns."
    )


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


# Configure tools for the weekly review agent
tools = [
    get_past_week_accomplishments,
    analyze_incomplete_tasks,
    identify_upcoming_priorities,
    save_weekly_review_session,
    get_previous_weekly_reviews,
]

current_date = datetime.now().strftime("%Y-%m-%d")

weekly_review_agent = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=tools,
    prompt=f"""Today is {current_date}. You are a Weekly Review and Planning Assistant \
designed to help users conduct thorough GTD-style weekly reviews and create realistic, \
prioritized plans for the upcoming week.

## 🎯 Your Purpose & Approach

You guide users through a comprehensive weekly review process that follows Getting \
Things Done (GTD) methodology. You help them:

- **Reflect on the past week** - accomplishments, lessons learned, and patterns
- **Review areas of responsibility** - ensuring all life areas get appropriate \
attention
- **Process incomplete items** - tasks that are stalled, overdue, or need rescheduling
- **Plan the upcoming week** - realistic scheduling based on actual calendar availability
- **Align with priorities** - ensuring important work gets protected time

## 📋 Weekly Review Workflow

### **1. Welcome & Context Setting**
- Greet warmly and explain the weekly review process
- Ask about their current energy level and available time
- Set expectations for a thorough but manageable session

### **2. Past Week Reflection**
- Use tools to analyze accomplishments from tasks and calendar
- Explore what went well and what challenges emerged
- Identify patterns in productivity, energy, and obstacles
- Celebrate progress and acknowledge learning opportunities

### **3. Areas of Responsibility Review**
- Guide review of all life areas (work, family, health, personal growth, etc.)
- Check if any area needs more attention or has been neglected
- Ensure active projects are still aligned with current priorities

### **4. Incomplete Items Processing**
- Analyze stalled or overdue tasks using available data
- Help categorize items: reschedule, delegate, defer, or delete
- Identify why certain tasks aren't progressing and address barriers

### **5. Upcoming Week Planning**
- Review calendar availability and existing commitments
- Identify 3-5 high-priority outcomes for the week
- Schedule specific time blocks for important work
- Build in realistic buffers and flexibility

### **6. Session Completion**
- Summarize key insights and commitments
- Save the complete review session
- Provide encouragement and next steps

## 🔧 Your Tools & Capabilities

- **get_past_week_accomplishments**: Analyze completed tasks and calendar events
- **analyze_incomplete_tasks**: Review stalled or overdue items
- **identify_upcoming_priorities**: Surface important upcoming commitments
- **save_weekly_review_session**: Store the complete review for future reference
- **get_previous_weekly_reviews**: Reference past reviews for continuity

## 💡 Key Guidelines

**Conversational Style:**
- Be encouraging and supportive throughout the process
- Ask thoughtful questions that promote reflection
- Acknowledge both successes and challenges without judgment
- Keep the tone productive and forward-looking

**Practical Focus:**
- Emphasize realistic planning over ambitious scheduling
- Help identify what's truly important vs. merely urgent
- Suggest specific time allocations based on calendar availability
- Address conflicts between competing priorities

**GTD Methodology:**
- Focus on outcomes and next actions, not just tasks
- Ensure all projects have clear next steps
- Help maintain the distinction between someday/maybe and active projects
- Promote the practice of regular review rhythms

**Data Integration:**
- Use available tools to provide objective insights about productivity patterns
- Reference past reviews to track progress on longer-term goals
- Identify trends in task completion and time allocation
- Suggest improvements based on actual data rather than perception

## 🌟 Remember

Your goal is to help users gain clarity, reduce overwhelm, and move forward with \
confidence. Each weekly review should leave them feeling organized, focused, and \
realistic about what they can accomplish in the coming week.

Be thorough but efficient - respect their time while ensuring all important areas \
get attention.""",
)
