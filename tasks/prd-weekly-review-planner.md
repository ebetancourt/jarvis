# Product Requirements Document: Weekly Review and Planner Agent

## Introduction/Overview

The Weekly Review and Planner Agent is a conversational AI agent designed to help busy knowledge workers conduct structured weekly reviews and planning sessions. Based on David Allen's Getting Things Done (GTD) methodology, this agent synthesizes information from task management systems, calendars, and journal entries to produce comprehensive weekly summaries and actionable plans for the upcoming week.

The primary goal is to help overwhelmed professionals maintain control over their multiple areas of responsibility (work, family, personal development) by providing a systematic review process that surfaces high-priority tasks, identifies patterns, and creates realistic weekly plans that match the user's actual capacity.

## Goals

1. **Reduce overwhelm** by providing structured weekly planning that breaks down responsibilities into manageable tasks
2. **Improve task completion rates** by creating realistic weekly plans that match user capacity
3. **Increase self-awareness** by identifying patterns and recurring themes from past week's activities
4. **Optimize time allocation** by suggesting specific calendar time slots for high-priority tasks
5. **Maintain continuity** by building on previous weekly reviews and tracking progress over time
6. **Support work-life balance** by considering all areas of responsibility (professional, personal, family)

## User Stories

**Primary User Story:**
As a busy knowledge worker and consultant with family responsibilities,
I want an AI agent to review my past week's activities and help me plan the upcoming week,
So that I can maintain control over my multiple responsibilities without feeling overwhelmed while ensuring I deliver value to clients and spend quality time with family.

**Supporting User Stories:**
- As a user, I want to see what I accomplished last week so that I can feel good about my progress and identify areas for improvement
- As a user, I want the system to identify recurring issues or stressors so that I can address them proactively
- As a user, I want specific time blocks suggested for my high-priority tasks so that I can realistically schedule my week
- As a user, I want to see conflicts between competing priorities so that I can make informed decisions about trade-offs
- As a user, I want my weekly plans to build on previous reviews so that I maintain momentum toward my goals

## Functional Requirements

### Core Review Process
1. **FR-001**: The system must conduct weekly reviews for Monday-Sunday time periods (configurable in future)
2. **FR-002**: The system must review Areas of Responsibility (husband, father, business owner, etc.) as the starting point
3. **FR-003**: The system must review active projects under each area of responsibility
4. **FR-004**: The system must analyze individual tasks within each project
5. **FR-005**: The system must reference the previous weekly review to assess progress and changes

### Data Integration
6. **FR-006**: The system must integrate with Todoist API to fetch tasks, projects, and labels
7. **FR-007**: The system must integrate with Google Calendar API to analyze past week events and upcoming week availability
8. **FR-008**: The system must support multiple Google accounts for calendar access
9. **FR-009**: The system must allow users to select which calendars from each Google account to include in the review process
10. **FR-010**: The system must provide OAuth configuration for Google accounts through the Streamlit application interface
11. **FR-011**: The system must access existing journaling data through the journaling agent tools
12. **FR-012**: The system must update task statuses and modifications back to Todoist
13. **FR-013**: The system must handle both recurring and one-time tasks without differentiation in processing

### Analysis and Insights
14. **FR-014**: The system must identify accomplished tasks and completed projects from the past week
15. **FR-015**: The system must detect recurring themes, concerns, or stressors from calendar events and journal entries
16. **FR-016**: The system must highlight uncompleted or stalled tasks by comparing current state to previous reviews
17. **FR-017**: The system must identify high-priority tasks for the upcoming week
18. **FR-018**: The system must propose specific calendar time slots for high-priority tasks based on available time

### Conflict Resolution
19. **FR-019**: The system must identify conflicting priorities when multiple high-priority tasks compete for the same time slots
20. **FR-020**: The system must present conflicts to the user with context and ask for direction
21. **FR-021**: The system must incorporate user decisions about priority conflicts into the final weekly plan

### Output and Storage
22. **FR-022**: The system must output weekly review results in formatted Markdown within the chat interface
23. **FR-023**: The system must store weekly review data as structured JSON in the database for future analysis
24. **FR-024**: The system must create actionable task lists with realistic volume that approaches but doesn't exceed user capacity
25. **FR-025**: The system must include specific time allocations and scheduling recommendations in the output

### Conversational Interface
26. **FR-026**: The system must operate as a conversational text chat agent that users can select from the agent array
27. **FR-027**: The system must handle sparse data gracefully by asking users about upcoming events and reviewing areas of responsibility
28. **FR-028**: The system must maintain conversation context throughout the review session

## Non-Goals (Out of Scope)

1. **Automatic scheduling** - The agent will suggest time blocks but not automatically create calendar events (future phase)
2. **Voice input/output** - Text-based interface only for initial version
3. **Multi-user support** - Designed for single-user self-hosted deployment
4. **Custom time periods** - Monday-Sunday only (though architecture should allow future configuration)
5. **Mobile-specific interface** - Web-based chat interface will be responsive but no native mobile app
6. **Integration with task managers other than Todoist** - Single integration initially
7. **Mood or energy tracking** - Focus on task and calendar data only initially
8. **Real-time notifications** - Manual trigger only for weekly reviews

## Design Considerations

### User Experience Flow
1. User configures OAuth connections for Google accounts and selects calendars in Streamlit application (one-time setup)
2. User selects "Weekly Review and Planner Agent" from agent dropdown
3. Agent initiates conversation by referencing previous weekly review (if available)
4. Agent presents past week accomplishments and identifies patterns from all configured calendars
5. Agent reviews areas of responsibility and active projects
6. Agent identifies and presents conflicting priorities for user resolution
7. Agent generates final weekly plan with specific time blocks
8. Agent saves structured data to database for future reference

### Configuration Interface
- **Streamlit OAuth Setup**: Users can authenticate multiple Google accounts through the web interface
- **Calendar Selection**: Users can enable/disable specific calendars from each connected account
- **Account Management**: Users can add, remove, or reconfigure Google account connections
- **Calendar Filtering**: Interface to exclude irrelevant calendars (e.g., shared calendars, holiday calendars)

### Output Format
- **Markdown formatting** for readability in chat interface
- **Structured sections**: Past Week Summary, Accomplishments, Recurring Themes, Upcoming Priorities, Time Block Suggestions, Action Items
- **JSON storage schema** for database persistence and future dashboard creation

## Technical Considerations

### Integration Requirements
- **Todoist OAuth setup** and API integration for task management
- **Multiple Google Calendar OAuth setup** and API integration for calendar analysis across multiple accounts
- **Streamlit OAuth configuration interface** for managing Google account connections
- **Calendar selection storage** to persist user's calendar preferences across accounts
- **Database schema design** for storing weekly review historical data and OAuth configurations
- **Integration with existing journaling agent tools** for accessing past journal entries

### Architecture
- **Standalone agent** in the existing agents.py array structure
- **Conversation memory** to maintain context during review session
- **Error handling** for API failures or sparse data scenarios
- **Timezone handling** for user's local timezone only

### Dependencies
- Existing journaling agent functionality and tools
- Existing Streamlit application infrastructure for OAuth configuration interface
- Todoist API credentials and permissions
- Google Calendar API credentials and permissions (supporting multiple account authentication)
- Database system for structured data storage and OAuth configuration persistence

## Success Metrics

### Quantitative Metrics
1. **User engagement**: Frequency of weekly review completions
2. **Task completion rate**: Percentage of planned tasks completed each week
3. **Session completion rate**: Percentage of users who complete full review sessions
4. **Data quality**: Successful API integrations and data retrieval rates

### Qualitative Metrics
1. **User sentiment analysis**: Analysis of user responses during reviews to gauge satisfaction
2. **Overwhelm reduction**: User self-reporting feeling more in control after reviews
3. **Work-life balance**: Evidence of balanced task allocation across areas of responsibility
4. **Capacity matching**: User feedback that planned work volume feels appropriate (challenging but achievable)

## Open Questions

1. **Database schema specifics**: What specific fields should be included in the JSON storage format for optimal future analysis?
2. **Conflict resolution UI**: What's the most effective way to present priority conflicts in a text chat interface?
3. **Integration fallbacks**: How should the system behave when external APIs (Todoist/Google Calendar) are temporarily unavailable?
4. **Historical data migration**: Should the system attempt to analyze historical data from before the agent's first use?
5. **Review frequency flexibility**: Should there be options for bi-weekly or monthly reviews in addition to weekly?
6. **Time estimation**: Should the agent attempt to estimate time requirements for suggested tasks?
7. **Notification system**: Should the system remind users when it's time for their weekly review?
8. **Multi-account authentication**: How should the system handle OAuth token refresh for multiple Google accounts simultaneously?
9. **Calendar conflict handling**: How should the system handle overlapping events across multiple calendars from different accounts?
10. **Streamlit OAuth flow**: Should the OAuth configuration be embedded in the existing Streamlit app or be a separate configuration page?
11. **Account linking**: Should the system support linking personal and work accounts with different privacy/access levels?

## Implementation Priority

### Phase 1 (MVP)
- Core review process (FR-001 through FR-005)
- Basic Todoist integration (FR-006, FR-012)
- Streamlit OAuth configuration interface (FR-010)
- Simple output formatting (FR-022)
- Conversational interface (FR-026 through FR-028)

### Phase 2
- Multiple Google Calendar integration (FR-007, FR-008, FR-009, FR-018)
- Journaling data access (FR-011)
- Database storage (FR-023)
- Conflict resolution (FR-019 through FR-021)

### Phase 3
- Advanced analysis (FR-014 through FR-017)
- Historical review comparison (FR-005, FR-024, FR-025)
- Success metrics tracking
- Performance optimization

---

*This PRD is designed to be implemented by a junior developer with clear, actionable requirements and sufficient context about the user's needs and workflow.*
