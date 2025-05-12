# All purpose personal assistant, indexes various knowledge bases and uses LLM to generate an answer

[![codecov](https://codecov.io/gh/ebetancourt/jarvis/branch/main/graph/badge.svg?token=MQMLQV473Z)](https://codecov.io/gh/ebetancourt/jarvis)

This project now uses [PDM](https://pdm.fming.dev/) for modern Python dependency and environment management.

This project indexes your data sources using LangChain and stores them in a Chroma AI database for efficient searching and retrieval.

This is being constructed iteratively, starting small. So far, it indexes:

- Your Obsidian notes

Knowledge Sources on the list:

- [x] Obsidian Notes
- [ ] GMail
- [ ] Google Calendar
- [ ] Manually managed memories
- [ ] Google Docs
- [ ] Screenpipe recordings
- [ ] Web Browsing history
- [ ] Limitless and Bee.computer AI wearable audio recordings
- [ ] Slack
- [ ] Discord
- [ ] WhatsApp
- [ ] iMessage
- [ ] Timing computer usage recording
- [ ] GitHub Activity
- [ ] Apple Health
- [ ] Social Media Activity
- [ ] Journal Entries (Day One?)

Also plan to add tools (MCP?) to

- [ ] Manage Tasks and Projects (Todoist)
- [ ] Manage Calendar entries
- [ ] Draft email messages
- [ ] Create Reminders
- [ ] Set Timers and alarms

As soon as we have some more useful items, it would be great to get Daily summaries from JARVIS

## Setup

1. **Install PDM** (if you don't have it):
   ```bash
   pip install pdm
   ```

2. **Install dependencies:**
   ```bash
   pdm install
   ```
   This will create a `.venv` and install all dependencies from `pyproject.toml`.

3. Configure the path to your Obsidian notes:
   - Copy `example-settings.yml` to `settings.yml`
   - Edit `settings.yml` and set the `obsidian_notes_path` to your Obsidian vault location
```yaml
obsidian_notes_path: /path/to/your/obsidian/notes
```

## Usage

- **Run the indexer script:**
  ```bash
  pdm run python index_notes.py
  ```

- **Run tests:**
  ```bash
  pdm run make test
  # or for coverage:
  pdm run make coverage
  ```
  Coverage HTML report will be in `htmlcov/index.html`.

- **Add dependencies:**
  ```bash
  pdm add <package>
  # For dev dependencies:
  pdm add --dev <package>
  ```

- **Activate the environment manually (optional):**
  ```bash
  pdm venv activate
  ```

## Continuous Integration

- All tests and coverage are run on every commit and pull request via GitHub Actions using PDM.
- Coverage is uploaded to Codecov and a badge can be added to the top of this README.

## Old Setup (no longer needed)
- You do **not** need to use `requirements.txt`, `venv`, or `pip install` directly.
- All dependency management is now handled by PDM and `pyproject.toml`.

## Project Features

- Indexes your Obsidian notes
- Indexes Gmail (and more sources planned)
- Uses LangChain, ChromaDB, and modern LLM tools

## Code Style

- Run linting with:
  ```bash
  pdm run make lint
  ```

The indexed notes can then be used for semantic search and other AI-powered operations.
