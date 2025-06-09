from datetime import datetime
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent

from plugins.obsidian.tool import search_notes

tools = [search_notes]
current_date = datetime.now().strftime("%Y-%m-%d")
jarvis_agent = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=tools,
    prompt=f"Today is {current_date}. You are a helpful assistant.",
)

# async def get_agent():
#     tools = await get_tools()
#     current_date = datetime.now().strftime("%Y-%m-%d")
#     graph = create_react_agent(
#         "anthropic:claude-3-7-sonnet-latest",
#         tools=tools,
#         prompt=f"Today is {current_date}. You are a helpful assistant.",
#     )
#     return graph.compile(checkpointer=MemorySaver(), store=InMemoryStore())


# @entrypoint(checkpointer=MemorySaver(), store=InMemoryStore())
# async def jarvis_agent(
#     inputs: dict[str, list[BaseMessage]],
#     *,
#     previous: dict[str, list[BaseMessage]],
#     config: RunnableConfig,
# ):
#     messages = inputs["messages"]
#     if previous:
#         messages = previous["messages"] + messages

#     graph = await get_agent()
#     response = await graph.ainvoke(messages)
#     return entrypoint.final(
#         value={"messages": [response]}, save={"messages": messages + [response]}
#     )
