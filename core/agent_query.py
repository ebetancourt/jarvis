from search_tools import search_notes, search_gmail
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from plugins.todoist.plugin import TodoistPlugin
import os
import asyncio
import re
import logging


# Initialize Todoist plugin
todoist_plugin = TodoistPlugin(os.getenv('TODOIST_API_TOKEN'))

# Initialize logger
logger = logging.getLogger(__name__)


# Wrap the search tools as LangChain tools
@tool("search_notes", return_direct=True)
def search_notes_tool(query: str) -> str:
    """Search your notes for relevant information."""
    result = search_notes(query)
    return result["result"]


@tool("search_gmail", return_direct=True)
def search_gmail_tool(query: str) -> str:
    """Search your Gmail for relevant information."""
    result = search_gmail(query)
    return result["result"]


@tool("search_todoist", return_direct=True)
async def search_todoist_tool(query: str) -> str:
    """Search your Todoist tasks."""
    result = await todoist_plugin.search(query)
    formatted_tasks = []
    for task in result:
        due = task['metadata'].get('due', {})
        due_str = f" (Due: {due})" if due else ""
        priority = "❗" * task['metadata'].get('priority', 1)
        formatted_tasks.append(f"{priority} {task['content']}{due_str}")

    if not formatted_tasks:
        return "No tasks found."
    return "\n".join(formatted_tasks)


def is_task_query(query: str) -> bool:
    """Determine if a query is task-related without using the LLM."""
    task_keywords = {
        'task', 'tasks', 'todo', 'todos', 'to-do', 'to do',
        'due', 'overdue', 'today', 'tomorrow', 'week',
        'remind', 'reminder', 'schedule', 'scheduled'
    }
    query_words = set(query.lower().split())
    return bool(query_words & task_keywords)


async def agent_query(query: str) -> dict:
    """Process a query and return relevant information."""

    # Direct routing for task-related queries
    if is_task_query(query):
        try:
            # Check for rescheduling requests
            if "reschedule" in query.lower() and ("overdue" in query.lower() or "due" in query.lower()):
                # Extract the target date if specified, default to "today"
                due_words = ["to", "for", "until"]
                due_string = "today"
                for word in due_words:
                    if word in query.lower():
                        parts = query.lower().split(word)
                        if len(parts) > 1:
                            due_string = parts[1].strip()
                            break

                # Handle overdue tasks specifically
                if "overdue" in query.lower():
                    result = await todoist_plugin.reschedule_overdue(due_string)
                else:
                    # Extract filter string from query
                    filter_string = "today"  # default
                    if "due" in query.lower():
                        filter_string = "overdue | today"  # include both overdue and today's tasks

                    result = await todoist_plugin.reschedule_tasks_by_filter(filter_string, due_string)

                return {
                    "result": result['message'],
                    "sources": result.get('tasks', []),
                    "distances": []
                }

            # Handle other task queries
            result = await todoist_plugin.search(query)
            if isinstance(result, dict) and 'success' in result:
                return {
                    "result": result['message'],
                    "sources": result.get('tasks', []),
                    "distances": []
                }
            elif not result:
                return {
                    "result": "No tasks found matching your query.",
                    "sources": [],
                    "distances": []
                }

            # Format task results
            formatted_tasks = []
            for task in result:
                formatted_task = {
                    'content': task['content'],
                    'source': task['source'],
                    'source_type': task['source_type'],
                    'metadata': task['metadata']
                }
                formatted_tasks.append(formatted_task)

            return {
                "result": f"Found {len(formatted_tasks)} matching tasks",
                "sources": formatted_tasks,
                "distances": []
            }

        except Exception as e:
            print(f"Error processing task query: {e}")
            return {
                "result": f"Error processing task query: {str(e)}",
                "sources": [],
                "distances": []
            }

    # For non-task queries, use the LLM-based agent
    try:
        llm = ChatOpenAI(temperature=0)
        agent = initialize_agent(
            tools=[search_notes_tool, search_gmail_tool],
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )

        result = await agent.arun(query)
        return {
            "result": result,
            "sources": [],  # Agent results don't have sources
            "distances": []
        }
    except Exception as e:
        return {
            "result": f"Error processing query: {str(e)}",
            "sources": [],
            "distances": []
        }


def llm_fallback(question: str):
    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7, max_tokens=1000)
    response = llm.invoke(question)
    return {"result": response.content if hasattr(response, 'content') else str(response), "sources": []}


def get_source_key(source, tool_source=None):
    # Returns a stable key for deduplication
    try:
        if hasattr(source, 'metadata'):
            meta = source.metadata
            if meta.get("source") == "obsidian":
                return ("obsidian", meta.get("item") or meta.get("file_path") or str(source))
            elif meta.get("source") == "Gmail":
                return ("gmail", meta.get("subject") or meta.get("item") or str(source))
            elif meta.get("source") == "todoist":
                return ("todoist", meta.get("task_id") or str(source))
        if isinstance(source, dict):
            if source.get("source") == "obsidian":
                return ("obsidian", source.get("item") or source.get("file_path") or str(source))
            elif source.get("source") == "Gmail":
                return ("gmail", source.get("subject") or source.get("item") or str(source))
            elif source.get("source") == "todoist":
                return ("todoist", source.get("task_id") or str(source))
        if isinstance(source, str):
            # Include the tool source in the key to prevent deduplication across tools
            return (tool_source or "str", source)
    except Exception:
        pass
    return ("other", str(source))


def deduplicate_sources(sources, tool_source=None):
    seen = set()
    unique_sources = []
    for source in sources:
        key = get_source_key(source, tool_source)
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)
    return unique_sources
