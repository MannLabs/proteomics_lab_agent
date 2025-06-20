"""database agent that can write and retrieve meta data to ms raw files into a data base"""

from pathlib import Path

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from . import prompt

PATH_TO_YOUR_MCP_SERVER_SCRIPT = str((Path(__file__).parent / "server.py").resolve())

MODEL = "gemini-2.0-flash-001"

database_agent = Agent(
   name="database_agent", # alternative name: db_mcp_client_agent
   model=MODEL,
    instruction=prompt.DB_MCP_PROMPT,
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="python3",
                args=[PATH_TO_YOUR_MCP_SERVER_SCRIPT],
            )
            # tool_filter=['list_tables'] # Optional: ensure only specific tools are loaded
        )
    ],
)
