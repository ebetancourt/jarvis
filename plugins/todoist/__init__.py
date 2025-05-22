import os
from dotenv import load_dotenv

load_dotenv()

plugin_path = os.path.dirname(os.path.abspath(__file__))
mcp_server_path = os.path.join(plugin_path, "mcp-server")


def get_todoist_mcp_server():
    return {
        "command": "uv",
        "args": [
            "--directory",
            mcp_server_path,
            "run",
            "main.py",
        ],
        "transport": "stdio",
        "env": {"TODOIST_API_TOKEN": os.getenv("TODOIST_API_TOKEN")},
    }
