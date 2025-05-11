# All purpose personal assistant, indexes various knowledge bases and uses LLM to generate an answer

[![codecov](https://codecov.io/gh/ebetancourt/jarvis/branch/main/graph/badge.svg?token=MQMLQV473Z)](https://codecov.io/gh/ebetancourt/jarvis)

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

1. Create a Python virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the path to your Obsidian notes:
   - Copy `example-settings.yml` to `settings.yml`
   - Edit `settings.yml` and set the `obsidian_notes_path` to your Obsidian vault location
```yaml
obsidian_notes_path: /path/to/your/obsidian/notes
```

## Usage

Run the indexer script to process your notes:
```bash
python index_notes.py
```

This will:
1. Load all markdown files from your Obsidian notes directory
2. Split them into manageable chunks
3. Create embeddings using HuggingFace's sentence transformers
4. Store the embeddings in a Chroma database in the `./chroma_db` directory

The indexed notes can then be used for semantic search and other AI-powered operations.

## Code Style

This project uses Black for code formatting and Flake8 for linting. To format your code:

```bash
black .
```

To check for code style issues:

```bash
flake8 .
```

The configuration for these tools can be found in:
- `pyproject.toml` - Black configuration
- `.flake8` - Flake8 configuration
