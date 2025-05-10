from search_tools import search_notes, search_gmail


def create_agent():
    # Placeholder for the real agent, will be mocked in tests
    pass


def agent_query(question: str):
    agent = create_agent()
    routing = agent.invoke(question)
    tool = routing.get("tool")
    if tool == "search_notes":
        notes_result = search_notes(question)
        return {
            "result": notes_result["result"],
            "sources": notes_result.get("source_documents", []),
        }
    elif tool == "search_gmail":
        gmail_result = search_gmail(question)
        return {
            "result": gmail_result["result"],
            "sources": gmail_result.get("source_documents", []),
        }
    elif tool == "both":
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
    else:
        return {"result": "Sorry, I could not route your query.", "sources": []}
