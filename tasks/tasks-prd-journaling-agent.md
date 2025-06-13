# Task List: Journaling Agent Implementation

## Relevant Files

- `src/agents/journaling_agent.py` - Main journaling agent implementation with LangGraph integration
- `src/agents/journaling_agent.test.py` - Unit tests for the journaling agent
- `src/tools/journal_tools.py` - Core journaling tools for file operations, search, and content processing (✓ Created with directory management and daily file creation functions)
- `src/tools/test_journal_tools.py` - Unit tests for journal tools (✓ Created with comprehensive test coverage, 11 tests passing)
- `src/agents/agents.py` - Updated to include the new journaling agent in the agent registry
- `src/data/journal/` - Directory for storing journal markdown files (to be created)

### Notes

- Unit tests should be placed alongside the code files they are testing
- Use `pytest` to run tests (following existing codebase patterns)
- Journal files will be stored in `/src/data/journal/` directory
- Follow existing agent patterns from `src/agents/jarvis.py` for LangGraph integration

## Tasks

- [ ] 1.0 Set up core file management and storage infrastructure
  - [x] 1.1 Create a function that ensures the existence of the `/src/data/journal/` directory structure with proper permissions
  - [x] 1.2 Implement `create_daily_file()` function that generates `YYYY-MM-DD.md` files
  - [ ] 1.3 Implement `format_file_title()` function to create titles like "# Friday, 13th of June 2025"
  - [ ] 1.4 Implement `add_timestamp_entry()` function to add entries with `## HH:MM:SS` format
  - [ ] 1.5 Implement `append_to_existing_file()` function for multiple daily entries
  - [ ] 1.6 Add error handling for file permissions, disk space, and directory creation issues
  - [ ] 1.7 Write unit tests for all file management functions

- [ ] 2.0 Implement guided prompting and conversation flow
  - [ ] 2.1 Create main conversation state management using LangGraph
  - [ ] 2.2 Implement `generate_guiding_questions()` function with CBT-style prompts
  - [ ] 2.3 Implement question flow logic (ask up to 2 questions, then process responses)
  - [ ] 2.4 Add completion signal detection ("I'm Done", empty responses)
  - [ ] 2.5 Create confirmation message system ("Great, saving this entry!")
  - [ ] 2.6 Design question bank focused on priorities, emotions, and deeper insights
  - [ ] 2.7 Implement conversation memory to avoid repeating questions within a session
  - [ ] 2.8 Write unit tests for conversation flow and question generation

- [ ] 3.0 Build content processing and summarization capabilities
  - [ ] 3.1 Implement `count_words()` function to check if entry exceeds 150 words
  - [ ] 3.2 Create `generate_summary()` function using AI to summarize long entries
  - [ ] 3.3 Ensure summaries are less than 1/5 the length of original entry
  - [ ] 3.4 Implement `format_summary_section()` to add "### Summary" heading
  - [ ] 3.5 Integrate summarization into the entry saving workflow
  - [ ] 3.6 Add configuration for summary length ratios and word count thresholds
  - [ ] 3.7 Write unit tests for summarization logic and formatting

- [ ] 4.0 Create search and retrieval functionality
  - [ ] 4.1 Implement frontmatter parsing for mood, keywords, and topics metadata
  - [ ] 4.2 Create `search_by_date_range()` function with start/end date parameters
  - [ ] 4.3 Implement `search_by_keywords()` function with full-text search
  - [ ] 4.4 Create `search_by_mood()` and `search_by_topics()` functions using frontmatter
  - [ ] 4.5 Implement `format_search_results()` with result count and file list (if <10)
  - [ ] 4.6 Create search result interaction options (full text, all files, ask questions)
  - [ ] 4.7 Implement `narrow_search()` functionality for refining results
  - [ ] 4.8 Add search result ranking and relevance scoring
  - [ ] 4.9 Write unit tests for all search and retrieval functions

- [ ] 5.0 Integrate journaling agent with existing agent framework
  - [ ] 5.1 Create `src/agents/journaling_agent.py` following `jarvis.py` pattern
  - [ ] 5.2 Import and configure journal tools as LangGraph tools
  - [ ] 5.3 Define agent prompt with journaling-specific instructions and personality
  - [ ] 5.4 Update `src/agents/agents.py` to include journaling agent in registry
  - [ ] 5.5 Add agent description: "A daily journaling assistant with guided prompts"
  - [ ] 5.6 Test agent selection and basic functionality through existing interface
  - [ ] 5.7 Implement proper error handling and graceful fallbacks for file operations
  - [ ] 5.8 Write integration tests for the complete journaling workflow
