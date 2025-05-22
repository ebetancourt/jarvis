import os
import logging
import json
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langgraph.graph import StateGraph, END, START

from search_tools import search_notes, search_gmail

# At the top of the file, alias the real search functions:
search_notes_fn = search_notes
search_gmail_fn = search_gmail

def search_notes_tool(search_notes=None, **state):
    logging.warning(f"[TOOL CALL] search_notes_tool called with query: {search_notes}")
    logging.warning(f"[TOOL CALL] search_notes_tool received state: {state}")
    result = search_notes_fn(search_notes)
    state = state or {}
    state = dict(state)
    state["search_notes"] = result["result"]
    state["search_notes_full"] = result  # For future source tracking
    return state

search_notes_tool = tool(
    "search_notes",
    return_direct=True,
    description="Search the user's notes for relevant information."
)(search_notes_tool)

def search_gmail_tool(search_gmail=None, **state):
    logging.warning(f"[TOOL CALL] search_gmail_tool called with query: {search_gmail}")
    logging.warning(f"[TOOL CALL] search_gmail_tool received state: {state}")
    result = search_gmail_fn(search_gmail)
    state = state or {}
    state = dict(state)
    state["search_gmail"] = result["result"]
    state["search_gmail_full"] = result  # For future source tracking
    return state

search_gmail_tool = tool(
    "search_gmail",
    return_direct=True,
    description="Search the user's Gmail for relevant information."
)(search_gmail_tool)

def tool_router_node(state):
    user_query = state["messages"][-1]["content"]
    tools = [
        {"name": "search_notes", "description": "Search the user's notes for relevant information."},
        {"name": "search_gmail", "description": "Search the user's Gmail for relevant information."}
    ]
    guidance = (
        "Always search notes, even for general knowledge queries. "
        "Search email if the question is about something specific in the user's life, "
        "an upcoming event, a past event, or anything related to subscriptions, purchases, receipts, or notifications. "
        "For each tool, rewrite the query to be optimal for that tool."
        "\n\n"
        "Examples:\n"
        "User: When is my Obsidian Sync renewal?\n"
        "Tools to use: search_notes (query: 'Obsidian Sync renewal date'), search_gmail (query: 'Obsidian Sync renewal receipt or notification')\n"
        "User: What did I write about Chris Pratt's workout?\n"
        "Tools to use: search_notes (query: 'Chris Pratt workout routine')\n"
    )
    llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.0, max_tokens=500)
    system_prompt = (
        f"You are a tool router. Available tools:\n"
        + "\n".join([f"- {t['name']}: {t['description']}" for t in tools])
        + f"\nGuidance: {guidance}\n"
        "Given the user query, respond in JSON with a list of tools to use and the rewritten query for each."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    response = llm.invoke(messages)
    try:
        parsed = json.loads(response.content)
        tools_to_use = parsed.get("tools_to_use") or parsed.get("tools")
        new_state = {"tools_to_use": tools_to_use, "messages": state["messages"]}
        for tool in tools_to_use or []:
            tool_key = tool.get("tool") or tool.get("name")
            if tool_key and tool.get("query"):
                new_state[tool_key] = tool["query"]
        return new_state
    except Exception as e:
        logging.error(f"Router LLM failed to parse JSON: {e}\nResponse: {response.content}")
        # fallback: just use notes
        return {"tools_to_use": [{"tool": "search_notes", "query": user_query}], "messages": state["messages"], "search_notes": user_query}

def create_agent():
    llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.0, max_tokens=500)
    tools = [search_notes_tool, search_gmail_tool]
    # Build the LangGraph graph
    builder = StateGraph(dict)
    builder.add_node("router", tool_router_node)
    builder.add_node("search_notes", search_notes_tool)
    builder.add_node("search_gmail", search_gmail_tool)
    # Routing logic: router -> tools as selected
    def route_tools(state):
        for tool_call in state.get("tools_to_use", []):
            tool_name = tool_call.get("tool") or tool_call.get("name")
            logging.warning(f"[ROUTER] Routing to tool: {tool_name}")
            yield tool_name
        yield END
    builder.add_edge(START, "router")
    builder.add_conditional_edges("router", route_tools)
    builder.add_edge("search_notes", END)
    builder.add_edge("search_gmail", END)
    graph = builder.compile()
    return graph

def agent_query(question: str, deduplicate_sources_flag: bool = True):
    if os.environ.get("JARVIS_TEST_MODE") == "1":
        return {"result": "This is a dummy answer.", "sources": ["dummy_source.md"]}
    state = {"messages": [{"role": "user", "content": question}]}
    agent = create_agent()
    result = agent.invoke(state)
    logging.warning(f"[FINAL STATE] {result}")
    tool_results = []
    if result.get("search_notes"):
        tool_results.append("Notes result: " + result["search_notes"])
    if result.get("search_gmail"):
        tool_results.append("Gmail result: " + result["search_gmail"])
    if tool_results:
        synthesis_prompt = (
            f"User question: {question}\n"
            f"Tool results:\n" +
            "\n".join(tool_results) +
            "\n\nCompose a helpful, precise answer for the user using the above information."
        )
        llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.0, max_tokens=500)
        response = llm.invoke([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": synthesis_prompt}
        ])
        final_result = response.content if hasattr(response, 'content') else str(response)
    else:
        final_result = "No answer found."
    return {
        "result": final_result,
        "sources": [],
        "distances": []
    }
