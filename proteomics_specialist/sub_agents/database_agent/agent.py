"""Database agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from pathlib import Path

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from proteomics_specialist.config import config

from . import prompt

PATH_TO_YOUR_MCP_SERVER_SCRIPT = str((Path(__file__).parent / "server.py").resolve())

MODEL = "gemini-2.5-flash"

database_agent = Agent(
    name="database_agent",
    model=config.model,
    description="An agent that can store and retrieve past evaluations of proteomics analysis results.",
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
