---
marp: true
theme: default
paginate: true
backgroundColor: #f8f9fa
color: #333
---

# Weekly Review Agent Architecture
## GTD-Based AI Assistant for Productivity Planning

---

## Overview

The Weekly Review Agent implements David Allen's GTD (Getting Things Done) methodology through an AI-powered assistant that helps users conduct systematic weekly reviews.

**Key Features:**
- 6-step GTD weekly review process
- Session state management
- Adaptive handling of sparse data
- Integration with external tools (Todoist, Calendar, Journal)
- Context-aware conversation flow

---

## Architecture Components

```python
# Core Components
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Tool Categories:
# 1. Session Management
# 2. Data Analysis  
# 3. Adaptive Handling
# 4. GTD Process Tools
```

**Main Components:**
- **Agent Core**: LangGraph React agent with Claude 3.5 Sonnet
- **Tool System**: 15+ specialized tools for different review aspects
- **Memory System**: Session state tracking and context management
- **Integration Layer**: Connects to Todoist, Google Calendar, and Journal

---

## Session Management Tools

### 1. Session Initialization
```python
@tool
def start_weekly_review_session(
    session_type: str = "full", 
    focus_areas: str = ""
) -> str:
    # Types: "full", "quick", "focused"
    # Returns structured guidance
```

### 2. Progress Tracking
```python
@tool
def track_review_progress(
    completed_steps: str, 
    current_step: str = "", 
    notes: str = ""
) -> str:
    # Tracks: clear, current, creative, projects, actions, calendar
```

---

## Data Analysis Tools

### Past Week Analysis
```python
@tool
def get_past_week_accomplishments(
    user_id: str, 
    start_date: str | None = None, 
    end_date: str | None = None
) -> str:
    # Fetches from Todoist completed tasks
    # Integrates Google Calendar events
    # Returns structured accomplishments summary
```

### Stalled Task Detection
```python
@tool
def analyze_incomplete_tasks(user_id: str) -> str:
    # Compares current tasks with previous reviews
    # Identifies recurring incomplete items
    # Suggests prioritization strategies
```

---

## Adaptive Data Handling

The agent gracefully handles scenarios with limited data availability:

### Data Assessment
```python
@tool
def assess_data_availability(
    data_sources: str = "tasks,calendar,journal"
) -> str:
    # Checks integration status
    # Recommends review approach
    # Suggests data improvement strategies
```

### Adaptive Review Process
```python
@tool
def adapt_review_for_sparse_data(
    available_data: str = "", 
    session_type: str = "adaptive"
) -> str:
    # Modifies process based on available data
    # Provides alternative approaches
```

---

## GTD Process Implementation

### The 6-Step GTD Weekly Review

1. **Get Clear** - Mind sweep and collection
2. **Get Current** - Review past week accomplishments
3. **Get Creative** - Areas of responsibility review
4. **Review Projects** - Active project status
5. **Review Actions** - Next actions lists
6. **Review Calendar** - Plan ahead

Each step has dedicated tools and guided prompts.

---

## Areas of Responsibility Framework

```python
@tool
def review_areas_of_responsibility_and_projects() -> str:
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
```

---

## Pattern Recognition & Insights

### Recurring Theme Detection
```python
@tool
def detect_recurring_themes_and_stressors(
    weeks: int = 4,
    stressor_keywords: list[str] = [
        "stress", "overwhelm", "anxiety", "blocked", 
        "frustration", "tired", "burnout", "conflict"
    ]
) -> str:
    # Analyzes journal entries for patterns
    # Identifies recurring stressors
    # Provides actionable insights
```

---

## User Interaction Flows

### Flow 1: Complete GTD Review (Full Data)

```
User: "I want to do my weekly review"
Agent: start_weekly_review_session(session_type="full")
       assess_data_availability()
       
1. Get Clear
   - Mind sweep guided questions
   - track_review_progress("clear")

2. Get Current  
   - get_past_week_accomplishments(user_id)
   - analyze_incomplete_tasks(user_id)
   - track_review_progress("clear,current")

3. Get Creative
   - review_areas_of_responsibility_and_projects()
   - track_review_progress("clear,current,creative")

4-6. Continue through remaining steps...
   - save_review_insights() at completion
```

---

### Flow 2: Quick Review (Limited Time)

```
User: "I only have 15 minutes for a quick review"
Agent: start_weekly_review_session(session_type="quick")
       adapt_review_for_sparse_data(session_type="minimal")

Process:
1. Quick Wins - What went well?
2. Key Priority - #1 focus for next week
3. Obstacle Check - What might interfere?
4. One Commitment - Clear next week commitment

Agent: save_review_insights(insights, commitments)
```

---

### Flow 3: Sparse Data Scenario

```
User: "I don't have much data tracked this week"
Agent: assess_data_availability()
       # Returns: Limited task data, missing calendar

Agent: adapt_review_for_sparse_data(available_data="limited tasks")
       guide_manual_weekly_reflection(focus_area="general")

Process:
- Manual reflection questions
- Memory-based accomplishment review
- Forward-planning focus
- suggest_data_improvement_strategies()
```

---

### Flow 4: Focused Review

```
User: "I want to focus on work projects this week"
Agent: start_weekly_review_session(
         session_type="focused", 
         focus_areas="work projects"
       )

Process:
- Targeted project review
- Work-related accomplishments analysis
- Professional area deep-dive
- Next actions for work projects
- manage_review_context() for insights
```

---

## Context Management

### Session State Tracking
```python
@tool
def manage_review_context(
    action: str,           # "set", "get", "list", "clear"
    key: str = "",         # Context key
    value: str = "",       # Context value
    context_type: str = "session"  # "session", "insights", "commitments"
) -> str:
```

**Usage Examples:**
- Store user's energy level: `manage_review_context("set", "energy", "low")`
- Remember key insight: `manage_review_context("set", "pattern", "meeting overload")`
- Retrieve for continuity: `manage_review_context("get", "current_step")`

---

## Integration Architecture

### External Tool Connections

```python
# Todoist Integration
from tools.todoist_tools import get_completed_tasks, get_all_tasks

# Calendar Integration  
from tools.calendar_tools import get_past_week_accomplishments

# Journal Integration
from tools.journal_tools import (
    search_by_keywords, 
    search_by_mood, 
    search_by_topics
)
```

**Data Flow:**
User → Agent → External APIs → Analysis Tools → Structured Output

---

## Agent Prompt Engineering

### Core Personality & Approach

```python
prompt = f"""Today is {current_date}. You are a Weekly Review and Planning Assistant 
designed to help users conduct thorough GTD-style weekly reviews following David 
Allen's Getting Things Done methodology.

## 🎯 GTD Weekly Review Purpose
The Weekly Review is the heart of the GTD system - a time to regain control and 
perspective, ensuring your system is current and your mind is clear.

## 🧠 Memory & Context Management
- start_weekly_review_session: Initialize sessions with proper context
- track_review_progress: Keep track of completed steps
- manage_review_context: Store and retrieve important information
- save_review_insights: Capture key insights and commitments
```

---

## Conversation Flow Patterns

### Pattern 1: Structured Progression
```
Agent: "Let's start your weekly review. How much time do you have?"
User: "About 45 minutes"
Agent: [start_weekly_review_session("full")]
       "Great! We'll do a complete 6-step review. Let's begin with getting clear..."
```

### Pattern 2: Adaptive Response
```
Agent: [assess_data_availability()]
       "I see you have limited task data. Let's adapt the review..."
       [adapt_review_for_sparse_data()]
       "We'll focus on reflection and forward planning."
```

### Pattern 3: Context Continuity
```
Agent: [track_review_progress("clear,current", "creative")]
       "We've completed the first two steps. Now let's review your areas of responsibility..."
       [manage_review_context("set", "key_insight", "too many interruptions")]
```

---

## Error Handling & Resilience

### Graceful Degradation
- **API Failures**: Fall back to manual reflection
- **Partial Data**: Adapt process to available information
- **Session Interruptions**: Resume with progress tracking
- **Integration Issues**: Provide alternative approaches

### Example Error Handling
```python
try:
    completed_tasks = get_completed_tasks(user_id)
except Exception as e:
    logger.warning(f"Error fetching tasks: {e}")
    # Fall back to manual reflection
    return guide_manual_weekly_reflection("accomplishments")
```

---

## Key Benefits

### For Users
- **Systematic Approach**: Follows proven GTD methodology
- **Adaptive Experience**: Works with any data availability
- **Context Awareness**: Maintains conversation continuity
- **Actionable Insights**: Provides specific next steps

### For Developers
- **Modular Design**: Easy to extend with new tools
- **Robust Error Handling**: Graceful degradation
- **Clear Separation**: Tools, logic, and presentation layers
- **Integration Ready**: Connects to existing productivity tools

---

## Future Enhancements

### Planned Features
- **Persistent Storage**: Save review history and insights
- **Advanced Analytics**: Trend analysis across multiple weeks
- **Custom Templates**: User-defined review processes
- **Integration Expansion**: More productivity tools
- **Mobile Support**: Streamlined mobile experience

### Technical Improvements
- **Caching Layer**: Reduce API calls for repeated data
- **Async Processing**: Parallel data fetching
- **Custom Memory**: Enhanced context management
- **Webhook Support**: Real-time data updates

---

## Conclusion

The Weekly Review Agent demonstrates how AI can enhance productivity methodologies by:

- **Automating routine tasks** while preserving human insight
- **Adapting to real-world constraints** like sparse data
- **Maintaining conversation context** for natural interaction
- **Integrating multiple data sources** for comprehensive analysis

The architecture balances flexibility with structure, ensuring users get value regardless of their current productivity setup.

---

## Questions & Discussion

**Contact:** 
- Repository: `/src/agents/weekly_review_agent.py`
- Integration: FastAPI service endpoints
- Usage: Streamlit app or direct API calls

**Key Discussion Points:**
- How to handle user privacy with personal data?
- What additional integrations would be most valuable?
- How to balance automation with user control?