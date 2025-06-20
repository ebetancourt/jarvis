# Tasks: Weekly Review and Planner Agent

Based on the PRD for the Weekly Review and Planner Agent, here is the complete implementation task breakdown:

## Relevant Files

- `src/agents/weekly_review_agent.py` - Main agent implementation with GTD-structured conversational interface, comprehensive areas of responsibility, David Allen's 6-step weekly review process, memory/context handling with session management tools, and graceful sparse data handling with adaptive review approaches.
- `src/agents/agents.py` - Agent registry with weekly review agent added as "weekly-review-agent".
- `src/streamlit_app.py` - Thin client Streamlit app with OAuth Management UI that calls backend API endpoints.
- `src/service/routes/oauth.py` - FastAPI OAuth management routes and endpoints.
- `src/service/oauth_service.py` - OAuth service layer for backend business logic.
- `src/schema/oauth_models.py` - Pydantic models for OAuth API requests and responses.
- `tests/agents/weekly_review_agent.test.py` - Unit tests for the weekly review agent.
- `src/tools/todoist_tools.py` - Todoist API integration tools for fetching and updating tasks/projects.
- `tests/tools/todoist_tools.test.py` - Unit tests for Todoist integration.
- `src/tools/calendar_tools.py` - Google Calendar multi-account integration tools.
- `tests/tools/calendar_tools.test.py` - Unit tests for calendar integration.
- `src/tools/weekly_review_tools.py` - Core weekly review analysis and processing tools.
- `tests/tools/weekly_review_tools.test.py` - Unit tests for weekly review tools.
- `src/schema/weekly_review_models.py` - Data models for weekly reviews, OAuth configs, and calendar settings.
- `src/common/oauth_manager.py` - Multi-service OAuth management utilities (Todoist + Google Calendar).
- `tests/common/oauth_manager.test.py` - Unit tests for OAuth management.
- `src/memory/weekly_reviews.py` - Database operations for storing/retrieving weekly review data.
- `tests/memory/weekly_reviews.test.py` - Unit tests for weekly review database operations.
- `requirements.txt` - Updated dependencies for Todoist API, Google Calendar API, additional OAuth libraries.

### Notes

- Unit tests should be placed in the tests directory following the directory structure of the project in src (tests for functions in src/tools/foo.py should be in tests/tools/foo.test.py).
- Use `npx jest [optional/path/to/test/file]` or `pytest [optional/path/to/test/file]` to run tests (depending on project setup).
- OAuth tokens and API credentials should be stored securely and never committed to version control.
- The agent should integrate with existing journaling agent tools from `src/tools/journal_tools.py`.

### Architecture Fix Required

**Current Issue:** Tasks 2.1-2.7 incorrectly embedded OAuth logic directly in the Streamlit app, violating the client-server architecture. The Streamlit app should be a thin frontend client that communicates with the FastAPI backend via HTTP/API calls.

**Solution:** Tasks 2.8-2.13 will restore proper architecture by:
- Moving OAuth logic to FastAPI backend service
- Creating proper API endpoints for OAuth operations
- Converting Streamlit to pure HTTP client
- Maintaining clean separation between frontend UI and backend business logic

## Tasks

- [x] 1.0 Create Weekly Review Agent Infrastructure
  - [x] 1.1 Create `src/agents/weekly_review_agent.py` with basic LangGraph agent structure
  - [x] 1.2 Add weekly review agent to `src/agents/agents.py` registry with proper description
  - [x] 1.3 Create agent prompt template that incorporates GTD methodology and areas of responsibility
  - [x] 1.4 Implement basic conversational interface with memory and context handling (FR-026, FR-028)
  - [x] 1.5 Add graceful handling for sparse data scenarios (FR-027)

- [ ] 2.0 Build Streamlit OAuth Configuration Interface
  - [x] 2.1 Create OAuth configuration page/section in existing `streamlit_app.py` (FR-010)
  - [x] 2.2 Implement Todoist OAuth authentication flow and token management
  - [x] 2.3 Implement Google account authentication flow with multiple account support
  - [x] 2.4 Build calendar selection interface for each connected Google account (FR-009)
  - [x] 2.5 Add account management features for both Todoist and Google (add, remove, reconfigure connections)
  - [x] 2.6 Create calendar filtering options to exclude irrelevant calendars
  - [x] 2.7 Implement settings persistence to database for all OAuth configurations (Todoist + Google)
  - [ ] 2.8 Revert Streamlit app to thin client architecture (remove embedded OAuth logic)
  - [ ] 2.9 Create OAuth API endpoints in FastAPI backend service
  - [ ] 2.10 Implement OAuth service layer in backend for proper separation
  - [ ] 2.11 Create OAuth management API routes (start, callback, status, disconnect)
  - [ ] 2.12 Update Streamlit OAuth Management button to use API endpoints
  - [ ] 2.13 Test and validate client-server OAuth flow end-to-end

## Task 2.8: Revert Streamlit App to Thin Client Architecture

**Objective:** Remove all embedded OAuth logic from Streamlit app and restore proper client-server separation

**Key Actions:**
- Remove `common.oauth_manager` imports and dependencies from `src/streamlit_app.py`
- Remove embedded OAuth functions: `start_todoist_oauth()`, `disconnect_todoist()`, `start_google_oauth()`, etc.
- Remove OAuth callback handling logic from Streamlit app
- Remove calendar management functions from Streamlit app
- Clean up Docker dependencies in client group (remove Google API libs, etc.)
- Restore Streamlit app to pure UI/HTTP client functionality

## Task 2.9: Create OAuth API Endpoints in FastAPI Backend Service

**Objective:** Design and implement comprehensive OAuth API endpoints in the backend service

**API Endpoints to Create:**
- `POST /api/oauth/todoist/start` - Initiate Todoist OAuth flow
- `POST /api/oauth/google/start` - Initiate Google OAuth flow
- `GET /api/oauth/callback/{service}` - Handle OAuth callbacks for both services
- `GET /api/oauth/status/{user_id}` - Get OAuth status for all services
- `DELETE /api/oauth/disconnect/{service}/{user_id}` - Disconnect specific service
- `POST /api/oauth/refresh/{service}/{user_id}` - Refresh specific token
- `GET /api/calendars/{user_id}` - Get calendar list for Google accounts
- `PUT /api/calendars/{user_id}/preferences` - Update calendar preferences

## Task 2.10: Implement OAuth Service Layer in Backend

**Objective:** Create proper service layer abstraction for OAuth operations in backend

**Components to Create:**
- `src/service/oauth_service.py` - OAuth business logic layer
- Move `src/common/oauth_manager.py` functionality to backend service
- Create OAuth service factory and dependency injection
- Implement proper error handling and validation
- Add OAuth operation logging and monitoring
- Create service-level OAuth health checks

## Task 2.11: Create OAuth Management API Routes

**Objective:** Implement complete OAuth management API with proper request/response models

**Implementation Details:**
- Create Pydantic models for OAuth requests/responses in `src/schema/oauth_models.py`
- Implement OAuth route handlers in `src/service/routes/oauth.py`
- Add proper authentication and authorization for OAuth endpoints
- Implement CORS handling for OAuth callback redirects
- Add comprehensive error handling with proper HTTP status codes
- Create OpenAPI documentation for OAuth endpoints

## Task 2.12: Update Streamlit OAuth Management Button

**Objective:** Redesign OAuth Management UI to use API endpoints instead of embedded logic

**Key Changes:**
- Replace embedded OAuth functions with HTTP client calls to backend API
- Update OAuth status loading to call `/api/oauth/status/{user_id}`
- Replace OAuth connection flows with API redirects to `/api/oauth/{service}/start`
- Update account management to use API disconnect/refresh endpoints
- Replace calendar management with API calls to `/api/calendars/*`
- Add proper error handling for API call failures
- Maintain existing UI/UX while using API backend

## Task 2.13: Test and Validate Client-Server OAuth Flow

**Objective:** Comprehensive testing of the new client-server OAuth architecture

**Testing Areas:**
- End-to-end OAuth flow testing (Todoist + Google)
- API endpoint integration testing
- Error handling and edge case validation
- Cross-browser OAuth callback testing
- Multi-user OAuth isolation testing
- Calendar preference synchronization testing
- OAuth token refresh and expiration handling
- Database persistence validation across client-server boundary

- [ ] 3.0 Implement Todoist API Integration
  - [ ] 3.1 Create `src/tools/todoist_tools.py` with functions to fetch tasks, projects, and labels (FR-006)
  - [ ] 3.2 Implement task status update functionality to sync changes back to Todoist (FR-012)
  - [ ] 3.3 Add support for handling both recurring and one-time tasks (FR-013)
  - [ ] 3.4 Implement error handling and fallback mechanisms for API failures
  - [ ] 3.5 Create comprehensive unit tests for all Todoist integration functions

- [ ] 4.0 Develop Google Calendar Multi-Account Integration
  - [ ] 4.1 Create `src/common/oauth_manager.py` for managing both Todoist and multiple Google account tokens (FR-008)
  - [ ] 4.2 Implement `src/tools/calendar_tools.py` with multi-account calendar data fetching (FR-007)
  - [ ] 4.3 Add calendar event analysis for past week accomplishments and upcoming availability
  - [ ] 4.4 Implement time slot analysis and availability detection for task scheduling (FR-018)
  - [ ] 4.5 Create calendar conflict detection across multiple accounts
  - [ ] 4.6 Add timezone handling for user's local timezone
  - [ ] 4.7 Implement OAuth token refresh handling for both Todoist and multiple Google accounts

- [ ] 5.0 Create Weekly Review Logic and Conversational Interface
  - [ ] 5.1 Implement core weekly review process following GTD methodology (FR-001, FR-002, FR-003, FR-004)
  - [ ] 5.2 Create areas of responsibility and active project review logic
  - [ ] 5.3 Develop past week accomplishment identification from tasks and calendar events (FR-014)
  - [ ] 5.4 Implement pattern detection for recurring themes and stressors (FR-015)
  - [ ] 5.5 Create logic to highlight uncompleted/stalled tasks by comparing to previous reviews (FR-016)
  - [ ] 5.6 Develop high-priority task identification for upcoming week (FR-017)
  - [ ] 5.7 Implement conflict resolution logic when priorities compete for time slots (FR-019, FR-020, FR-021)
  - [ ] 5.8 Create Markdown output formatting for chat interface (FR-022)
  - [ ] 5.9 Develop realistic task volume calculation to match user capacity (FR-024)
  - [ ] 5.10 Add specific time allocation and scheduling recommendations (FR-025)
  - [ ] 5.11 Integrate with existing journaling agent tools for journal data access (FR-011)

- [ ] 6.0 Implement Database Storage and Historical Tracking
  - [ ] 6.1 Design database schema for weekly review data storage in `src/schema/weekly_review_models.py`
  - [ ] 6.2 Create `src/memory/weekly_reviews.py` for database operations (FR-023)
  - [ ] 6.3 Implement structured JSON storage for weekly review sessions
  - [ ] 6.4 Add OAuth configuration and calendar settings persistence
  - [ ] 6.5 Create functionality to reference previous weekly reviews for continuity (FR-005)
  - [ ] 6.6 Implement historical data retrieval and comparison logic
  - [ ] 6.7 Add data migration support for future schema changes
  - [ ] 6.8 Create comprehensive unit tests for all database operations
