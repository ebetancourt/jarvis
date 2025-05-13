#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import argparse
import sys
import asyncio
from core.agent_query import agent_query
from plugins.todoist.server import complete_task_by_name

def format_source(source, distance=None):
    # If it's a Document object with metadata, extract info
    try:
        if hasattr(source, 'metadata'):
            meta = source.metadata
            if meta.get("source") == "obsidian":
                rel_path = meta.get("item") or meta.get("file_path") or "Unknown file"
                s = f"Obsidian: {rel_path}"
            elif meta.get("source") == "Gmail":
                subject = meta.get("subject") or meta.get("item") or "Gmail message"
                s = f"Gmail: {subject}"
            elif meta.get("source") == "todoist":
                content = meta.get("content", "Unknown task")
                project = f" (Project: {meta.get('project_name')})" if meta.get('project_name') else ""
                due = f" (Due: {meta.get('due')})" if meta.get('due') else ""
                s = f"Todoist: {content}{project}{due}"
            else:
                s = str(source)
        elif isinstance(source, dict):
            if source.get("source") == "obsidian":
                rel_path = source.get("item") or source.get("file_path") or "Unknown file"
                s = f"Obsidian: {rel_path}"
            elif source.get("source") == "Gmail":
                subject = source.get("subject") or source.get("item") or "Gmail message"
                s = f"Gmail: {subject}"
            elif source.get("source") == "todoist":
                content = source.get("content", "Unknown task")
                project = f" (Project: {source.get('project_name')})" if source.get('project_name') else ""
                due = f" (Due: {source.get('due')})" if source.get('due') else ""
                s = f"Todoist: {content}{project}{due}"
            else:
                s = str(source)
        elif isinstance(source, str):
            s = source
        else:
            s = str(source)
    except Exception:
        s = str(source)

    if distance is not None:
        s = f"{s} (score: {distance:.2f})"
    return s

def get_source_key(source):
    # Returns a stable key for deduplication
    try:
        if hasattr(source, 'metadata'):
            meta = source.metadata
            if meta.get("source") == "obsidian":
                return ("obsidian", meta.get("item") or meta.get("file_path") or str(source))
            elif meta.get("source") == "Gmail":
                return ("gmail", meta.get("subject") or meta.get("item") or str(source))
        if isinstance(source, dict):
            if source.get("source") == "obsidian":
                return ("obsidian", source.get("item") or source.get("file_path") or str(source))
            elif source.get("source") == "Gmail":
                return ("gmail", source.get("subject") or source.get("item") or str(source))
        if isinstance(source, str):
            return ("str", source)
    except Exception:
        pass
    return ("other", str(source))

async def main():
    parser = argparse.ArgumentParser(description='Jarvis CLI')
    parser.add_argument('query', help='The query to process')
    args = parser.parse_args()

    # Check if this is a task completion command
    if any(phrase in args.query.lower() for phrase in ['mark', 'complete', 'done', 'finish']):
        # Extract task name from the query
        task_name = args.query.lower()
        for phrase in ['mark', 'complete', 'done', 'finish', 'as']:
            task_name = task_name.replace(phrase, '')
        task_name = task_name.strip()

        result = await complete_task_by_name(task_name)
        print("\nAnswer:")
        print(result['message'])
        return

    # For other queries, use the regular agent_query
    result = await agent_query(args.query)
    print("\nAnswer:")
    print(result['result'])

    if result.get('sources'):
        print("\nSources:")
        for source in result['sources']:
            print(f"- {format_source(source)}")

if __name__ == '__main__':
    asyncio.run(main())
