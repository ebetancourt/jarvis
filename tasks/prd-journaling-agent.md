# Product Requirements Document: Journaling Agent

## Introduction/Overview

The Journaling Agent is a LangGraph-based AI assistant designed to help users maintain a daily journaling practice through conversational interaction. This agent serves as the foundation for a larger life-organization AI personal assistant system. By facilitating regular journaling through guided prompts and questions, the agent helps users capture their thoughts, goals, concerns, and daily experiences in a structured markdown format. The journal entries will serve as memory and context for future AI assistant capabilities, while also providing immediate cognitive behavioral therapy (CBT) benefits through guided introspection.

**Problem Solved:** Many people recognize the value of daily journaling for introspection and mental clarity but struggle to maintain the practice due to time constraints, uncertainty about what to write, or feeling overwhelmed by their responsibilities.

## Goals

1. **Enable Consistent Journaling:** Reduce friction for daily journaling through conversational AI guidance
2. **Capture Rich Context:** Extract deeper goals, concerns, and motivations through thoughtful prompting
3. **Provide CBT Benefits:** Help users process overwhelm and anxiety by organizing thoughts and identifying actionable priorities
4. **Create Searchable Memory:** Build a structured knowledge base of personal experiences for future AI assistant capabilities
5. **Support Life Planning:** Document learning, projects, successes, and failures to inform future decision-making

## User Stories

1. **As a busy professional**, I want to quickly brain-dump my day's thoughts and experiences so that I can process my feelings and identify what's actually important without spending too much time writing.

2. **As someone who feels overwhelmed**, I want the agent to ask me guiding questions that help me articulate my concerns and priorities so that I can see my situation more clearly and feel less anxious.

3. **As a lifelong learner**, I want to document what I learned and worked on each day so that I can track my growth and reference past insights.

4. **As someone working on personal development**, I want to reflect on what went right and wrong each day so that I can identify patterns and areas for improvement.

5. **As a user of the future AI assistant**, I want my journal entries to be searchable and accessible so that the AI can understand my context, goals, and personality over time.

## Functional Requirements

### Core Journaling Functionality
1. **Daily Journal Creation:** The system must create one markdown file per day with the naming format `YYYY-MM-DD.md` (e.g., `2025-06-13.md`)
2. **File Title Format:** Each daily file must have a title in the format `# <DAY OF THE WEEK>, <CARDINAL DATE> of <MONTH> <YEAR>` (e.g., `# Friday, 13th of June 2025`)
3. **Entry Timestamps:** Each individual journal entry must be timestamped with a second-level heading in the format `## HH:MM:SS` (e.g., `## 16:30:00`)
4. **Entry Appending:** Multiple entries on the same day must be appended to the existing daily file
5. **File Storage:** All journal files must be stored in `/src/data/journal/` directory

### Guided Prompting
6. **Question Generation:** The agent must ask up to two guiding or clarifying questions to help users capture their thoughts more completely
7. **Session Completion:** The agent must recognize completion signals ("I'm Done" or empty responses) and confirm entry saving with "Great, saving this entry!"
8. **CBT-Style Prompting:** Questions should be designed to help users identify priorities, process emotions, and extract deeper insights

### Content Processing
9. **Auto-Summarization:** The system must generate a summary for entries longer than 150 words
10. **Summary Length:** Summaries must be less than 1/5 the length of the original entry
11. **Summary Format:** Summaries must be included under a third-level heading `### Summary`

### Retrieval Capabilities
12. **Search Functionality:** The agent must support searching past entries by date range, keywords, mood, and topics
13. **Metadata Support:** The system should support frontmatter in markdown files for tagging mood, keywords, and topics
14. **Search Results Display:** Search results must show:
    - Summary of retrieved entries with result count
    - List of matching files (if fewer than 10 results)
    - Options to view full text of specific files or all files
    - Option to ask questions using retrieved entries as context
    - Option to narrow search further

### Integration
15. **Agent Framework:** The journaling agent must integrate with the existing agent structure in `src/agents/agents.py`
16. **Agent Selection:** The agent must be selectable from the existing agent list alongside other agents

## Non-Goals (Out of Scope)

- **Entry Editing/Deletion:** Users cannot edit or delete previous entries through the agent in v1
- **Backdating Entries:** Users cannot add entries for previous dates (feature not yet implemented message should be shown)
- **Proactive Suggestions:** The agent will not proactively suggest journaling times
- **Advanced Analytics:** No mood tracking, sentiment analysis, or statistical reporting in v1
- **Export Functionality:** No export to other formats or platforms in v1
- **Multi-user Support:** Single-user system only
- **Real-time Collaboration:** No sharing or collaborative features

## Design Considerations

- **Conversational Interface:** All interactions should feel natural and supportive, not clinical
- **Minimal Friction:** Entry process should be as streamlined as possible
- **Consistent Format:** Maintain strict markdown formatting for future parsing and AI consumption
- **Extensible Structure:** Design with future AI assistant integration in mind

## Technical Considerations

- **File Operations:** Use standard Python file I/O operations for markdown file creation and management
- **Date/Time Handling:** Implement proper timezone handling for timestamps and file naming
- **Error Handling:** Graceful handling of file permission issues and storage errors
- **LangGraph Integration:** Follow existing patterns from other agents in the codebase (reference `jarvis.py` structure)
- **Dependencies:** Minimize external dependencies beyond basic file operations and LangGraph requirements

## Success Metrics

1. **Usage Consistency:** User creates journal entries at least 5 days per week
2. **Entry Quality:** Average entry length increases over time (indicating deeper reflection)
3. **Question Engagement:** User responds to guiding questions at least 80% of the time
4. **Search Utilization:** User retrieves past entries at least once per week
5. **User Satisfaction:** Subjective feeling of reduced overwhelm and increased clarity

## Open Questions

1. **Timezone Handling:** How should the agent handle journaling across different time zones or at midnight transitions?
2. **File Permissions:** What should happen if the `/src/data/journal/` directory doesn't exist or isn't writable?
3. **Entry Length Limits:** Should there be any maximum length limits for individual entries?
4. **Mood/Topic Tagging:** What specific mood and topic categories should be supported in frontmatter?
5. **Search Ranking:** How should search results be ranked when multiple entries match criteria?
6. **Performance:** At what point (number of journal files) might search performance become a concern?

---

**Document Version:** 1.0
**Created:** 2025-01-09
**Target Implementation:** Q1 2025
