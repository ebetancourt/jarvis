# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install dependencies with uv (recommended)
pip install uv
uv sync --frozen
source .venv/bin/activate

# Or with pip
pip install .
```

### Running Services
```bash
# Run FastAPI service
python src/run_service.py

# Run Streamlit app
streamlit run src/streamlit_app.py

# Run client example
python src/run_client.py
```

### Docker Development
```bash
# Development with auto-reload
docker compose watch

# Standard compose
docker compose up --build
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/agents/test_journaling_agent.py

# Run integration tests
pytest tests/integration/
```

### Code Quality
```bash
# Format code
ruff format

# Lint code
ruff check

# Type checking
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

## Architecture Overview

This is an AI agent service toolkit built with LangGraph, FastAPI, and Streamlit. The architecture follows a modular design with clear separation of concerns:

### Core Components

**Agent System (`src/agents/`)**: Multiple specialized agents including:
- `jarvis_agent`: Main conversational agent
- `research_assistant`: Web search and calculator capabilities
- `rag_assistant`: Retrieval-augmented generation with ChromaDB
- `journaling_agent`: Daily journaling with guided prompts
- `weekly_review_agent`: GTD-style weekly planning
- Agent registry in `agents.py` manages all available agents

**Service Layer (`src/service/`)**: FastAPI application serving agents via REST API
- Supports both streaming and non-streaming endpoints
- Authentication with optional header-based auth
- OAuth integration for calendar and external services
- Agent endpoints: `/{agent_name}/invoke` and `/{agent_name}/stream`

**Client Interface (`src/client/`)**: Generic `AgentClient` for programmatic access
- Supports sync/async invocations
- Handles streaming and non-streaming responses
- Used by Streamlit app and can be used by other applications

**Schema (`src/schema/`)**: Pydantic models defining protocol contracts
- `UserInput`, `ChatMessage`, `StreamInput` for API communication
- `AgentInfo` for agent metadata
- OAuth models for authentication flows

**Memory System (`src/memory/`)**: Persistent storage for agent conversations
- Supports SQLite (default), PostgreSQL, and MongoDB
- LangGraph checkpoints for conversation state
- OAuth token storage

**Settings (`src/core/settings.py`)**: Centralized configuration
- Supports multiple LLM providers (OpenAI, Anthropic, Google, etc.)
- Database configuration
- Feature flags and thresholds
- Environment-based configuration with Pydantic

**Authentication System (`src/service/auth_service.py`, `src/service/routes/auth.py`)**:
- Google OAuth-based login using same OAuth app as Calendar integration
- JWT session tokens with 30-day expiration and refresh capability
- User account mapping (Google account ↔ internal user ID)
- Session management with database persistence
- Login endpoints: `/api/auth/login/start`, `/api/auth/login/callback`, `/api/auth/status`

### Agent Web Kit (`agent-web-kit/`)
Next.js frontend providing modern web interface:
- Real-time streaming chat
- Thread management
- Model and agent selection
- Built with React, TypeScript, and Tailwind CSS

### Key Integrations
- **LangGraph**: Agent orchestration and state management
- **LangSmith**: Tracing and observability
- **ChromaDB**: Vector storage for RAG capabilities
- **OAuth**: Google Calendar and other service integrations
- **Docker**: Multi-service development environment

### Environment Variables
Essential configuration (see `example.env`):
- At least one LLM API key required (e.g., `OPENAI_API_KEY`)
- Database settings for persistence
- **Google OAuth for login**: `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`
- **Login redirect URIs**: `GOOGLE_LOGIN_REDIRECT_URI`, `STREAMLIT_URL`
- Optional: LangSmith tracing, additional OAuth credentials
- Journaling thresholds and feature flags

### Testing Strategy
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Service tests for API endpoints
- Docker-based E2E testing
- pytest with async support and fixtures