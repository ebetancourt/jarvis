from search_tools import search_notes, search_gmail
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
import os
import asyncio
import re
import logging


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


async def agent_query(query: str) -> dict:
    """Process a query and return relevant information."""
    # Use the LLM-based agent for all queries
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
        if isinstance(source, dict):
            if source.get("source") == "obsidian":
                return ("obsidian", source.get("item") or source.get("file_path") or str(source))
            elif source.get("source") == "Gmail":
                return ("gmail", source.get("subject") or source.get("item") or str(source))
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
