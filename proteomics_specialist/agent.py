import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters

from . import prompt

# MODEL = "gemini-2.5-pro-preview-03-25"
MODEL = "gemini-2.0-flash-001"

MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")


root_agent = LlmAgent(
   name="MongoDB_MCP_Agent",
   model=MODEL,
   # description="Agent to answer questions about mass spectrometer performance using search results provided by a database.",
   instruction=prompt.DB_MCP_PROMPT,
   tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="docker",
                    args=[
                        "run",
                        "--rm",
                        "-i",
                        "-e",
                        f"MDB_MCP_CONNECTION_STRING={MONGODB_CONNECTION_STRING}",
                        "mongodb/mongodb-mcp-server:latest"
                    ]
                )
            )
        ),
   ]
)