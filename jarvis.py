#!/usr/bin/env python3
import argparse
from datetime import datetime
import sys
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from plugins.tools import tools

load_dotenv()


current_date = datetime.now().strftime("%Y-%m-%d")
graph = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=tools,
    prompt=f"Today is {current_date}. You are a helpful assistant.",
)


def main():
    parser = argparse.ArgumentParser(description="Ask Jarvis a question.")
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

    inputs = {"messages": [{"role": "user", "content": question}]}
    for chunk in graph.stream(inputs, stream_mode="updates"):
        print(chunk)


if __name__ == "__main__":
    main()
