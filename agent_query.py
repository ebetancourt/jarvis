from search_tools import search_notes, search_gmail
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType


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


def create_agent():
    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.0, max_tokens=500)
    tools = [search_notes_tool, search_gmail_tool]
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=False,
        handle_parsing_errors=True,
    )
    return agent


def agent_query(question: str):
    q = (question or "").lower()
    if (
        ("note" in q and "email" in q)
        or ("both" in q)
        or ("everything" in q)
        or ("all" in q)
    ):
        notes_result = search_notes(question)
        gmail_result = search_gmail(question)
        combined_result = f"{notes_result['result']}\n{gmail_result['result']}"
        combined_sources = list(notes_result.get("source_documents", [])) + list(
            gmail_result.get("source_documents", [])
        )
        return {
            "result": combined_result,
            "sources": combined_sources,
        }
    elif "note" in q:
        notes_result = search_notes(question)
        return {
            "result": notes_result["result"],
            "sources": notes_result.get("source_documents", []),
        }
    elif "email" in q or "gmail" in q:
        gmail_result = search_gmail(question)
        return {
            "result": gmail_result["result"],
            "sources": gmail_result.get("source_documents", []),
        }
    else:
        # Default: try both
        notes_result = search_notes(question)
        gmail_result = search_gmail(question)
        combined_result = f"{notes_result['result']}\n{gmail_result['result']}"
        combined_sources = list(notes_result.get("source_documents", [])) + list(
            gmail_result.get("source_documents", [])
        )
        return {
            "result": combined_result,
            "sources": combined_sources,
        }
