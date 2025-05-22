from plugins.obsidian.tool import search_notes
from plugins.gmail.tool import search_gmail
from plugins.tavilyWebSearch.tool import search_tool
from langgraph.prebuilt import ToolNode

tools = [search_notes, search_gmail, search_tool]

tool_node = ToolNode(tools)
