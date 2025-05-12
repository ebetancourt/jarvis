#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import argparse
import sys
from core.agent_query import agent_query

def format_source(source):
    # If it's a Document object with metadata, extract info
    try:
        if hasattr(source, 'metadata'):
            meta = source.metadata
            if meta.get("source") == "obsidian":
                rel_path = meta.get("item") or meta.get("file_path") or "Unknown file"
                return f"Obsidian: {rel_path}"
            elif meta.get("source") == "Gmail":
                subject = meta.get("subject") or meta.get("item") or "Gmail message"
                return f"Gmail: {subject}"
        # If it's a dict (sometimes returned by some chains)
        if isinstance(source, dict):
            if source.get("source") == "obsidian":
                rel_path = source.get("item") or source.get("file_path") or "Unknown file"
                return f"Obsidian: {rel_path}"
            elif source.get("source") == "Gmail":
                subject = source.get("subject") or source.get("item") or "Gmail message"
                return f"Gmail: {subject}"
        # If it's a string, just return it
        if isinstance(source, str):
            return source
    except Exception:
        pass
    return str(source)

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

def main():
    parser = argparse.ArgumentParser(
        description="Ask Jarvis a question. The agent will search your notes, Gmail, or both as appropriate."
    )
    parser.add_argument(
        "question",
        type=str,
        nargs=argparse.REMAINDER,
        help="Your question for Jarvis (in natural language)",
    )
    args = parser.parse_args()

    if not args.question or not any(word.strip() for word in args.question):
        print("Error: Please provide a question to ask Jarvis.")
        parser.print_help()
        sys.exit(1)

    question = " ".join(args.question).strip()
    try:
        result = agent_query(question)
        print("\nAnswer:")
        print(result.get("result", "No answer returned."))
        sources = result.get("sources", [])
        # Deduplicate sources by a stable key
        seen = set()
        unique_sources = []
        for source in sources:
            key = get_source_key(source)
            if key not in seen:
                seen.add(key)
                unique_sources.append(source)
        if unique_sources:
            print("\nSources:")
            for source in unique_sources:
                print(f"- {format_source(source)}")
        else:
            print("\nSources: None found.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
