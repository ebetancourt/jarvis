#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import argparse
import sys
import asyncio
from core.agent_query import agent_query

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
            else:
                s = str(source)
        elif isinstance(source, dict):
            if source.get("source") == "obsidian":
                rel_path = source.get("item") or source.get("file_path") or "Unknown file"
                s = f"Obsidian: {rel_path}"
            elif source.get("source") == "Gmail":
                subject = source.get("subject") or source.get("item") or "Gmail message"
                s = f"Gmail: {subject}"
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

    # Process the query using agent_query
    result = await agent_query(args.query)
    print("\nAnswer:")
    print(result['result'])

    if result.get('sources'):
        print("\nSources:")
        for source in result['sources']:
            print(f"- {format_source(source)}")

if __name__ == '__main__':
    asyncio.run(main())
