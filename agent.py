# my_agent/agent.py
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, END, START
from core.nodes import call_model, should_continue  # import nodes
from core.state import AgentState  # import state
from dotenv import load_dotenv
from tools import tool_node

load_dotenv()


# Define the config
class GraphConfig(TypedDict):
    model_name: Literal["anthropic", "openai"]


workflow = StateGraph(AgentState, config_schema=GraphConfig)
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)
workflow.add_edge("action", "agent")

graph = workflow.compile()
