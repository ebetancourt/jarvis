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


def llm_fallback(question: str):
    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7, max_tokens=1000)
    response = llm.invoke(question)
    return {"result": response.content if hasattr(response, 'content') else str(response), "sources": []}


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


def deduplicate_sources(sources):
    seen = set()
    unique_sources = []
    for source in sources:
        key = get_source_key(source)
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)
    return unique_sources


def agent_query(question: str, deduplicate_sources_flag: bool = True):
    q = (question or "").lower()
    if (
        ("note" in q and "email" in q)
        or ("both" in q)
        or ("everything" in q)
        or ("all" in q)
    ):
        notes_result = search_notes(question)
        gmail_result = search_gmail(question)

        # Combine results, ensuring no duplication
        notes_text = notes_result['result'].strip()
        gmail_text = gmail_result['result'].strip()

        # Only add newline between results if both have content
        combined_result = ""
        if notes_text and gmail_text:
            combined_result = f"{notes_text}\n\n{gmail_text}"
        else:
            combined_result = notes_text or gmail_text

        sources_concat = list(notes_result.get("source_documents", [])) + list(gmail_result.get("source_documents", []))
        combined_sources = deduplicate_sources_flag(sources_concat) if deduplicate_sources_flag else sources_concat

        if not combined_result.strip():
            return llm_fallback(question)

        return {
            "result": combined_result,
            "sources": combined_sources,
            "distances": notes_result.get("distances", [])  # Only include notes distances for now
        }
    elif "note" in q:
        notes_result = search_notes(question)
        if not notes_result["result"].strip():
            return llm_fallback(question)
        return {
            "result": notes_result["result"],
            "sources": notes_result.get("source_documents", []),
            "distances": notes_result.get("distances", [])
        }
    elif "email" in q or "gmail" in q:
        gmail_result = search_gmail(question)
        if not gmail_result["result"].strip():
            return llm_fallback(question)
        return {
            "result": gmail_result["result"],
            "sources": gmail_result.get("source_documents", []),
            "distances": []  # Gmail doesn't have distances yet
        }
    else:
        # Default: try both, but if both are empty, fallback to LLM
        notes_result = search_notes(question)
        gmail_result = search_gmail(question)

        # Combine results, ensuring no duplication
        notes_text = notes_result['result'].strip()
        gmail_text = gmail_result['result'].strip()

        # Only add newline between results if both have content
        combined_result = ""
        if notes_text and gmail_text:
            combined_result = f"{notes_text}\n\n{gmail_text}"
        else:
            combined_result = notes_text or gmail_text

        sources_concat = list(notes_result.get("source_documents", [])) + list(gmail_result.get("source_documents", []))
        combined_sources = deduplicate_sources(sources_concat) if deduplicate_sources_flag else sources_concat

        if not combined_result.strip() or "could not route" in combined_result.lower():
            return llm_fallback(question)

        return {
            "result": combined_result,
            "sources": combined_sources,
            "distances": notes_result.get("distances", [])  # Only include notes distances for now
        }
