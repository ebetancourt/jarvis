from langgraph.prebuilt import ToolNode

# from langchain_mcp_adapters.client import MultiServerMCPClient
from plugins.obsidian.tool import search_notes

# from plugins.gmail.tool import search_gmail
# from plugins.tavilyWebSearch.tool import search_tool
# from plugins.todoist import get_todoist_mcp_server

# mcp_servers = {
#     "todoist": get_todoist_mcp_server(),
# }
# mcp_client = MultiServerMCPClient(mcp_servers)


async def get_tools():
    # tools = await mcp_client.get_tools()
    # tools.extend([search_notes, search_gmail, search_tool])
    tools = [search_notes]
    return tools


async def get_tool_node():
    tools = await get_tools()
    return ToolNode(tools)
