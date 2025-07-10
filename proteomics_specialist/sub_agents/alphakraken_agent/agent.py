"""alphakraken agent can retrieve proteomics analysis results"""

import os

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters

from . import prompt

MODEL = "gemini-2.5-flash" # "gemini-2.0-flash-001" might have lower latency.

KRAKEN_PORT = os.getenv("KRAKEN_PORT")
KRAKEN_HOST = os.getenv("KRAKEN_HOST")
KRAKEN_USER = os.getenv("KRAKEN_USER")
KRAKEN_PASSWORD = os.getenv("KRAKEN_PASSWORD")

alphakraken_agent = Agent(
   name="alphakraken_agent",
   model=MODEL,
   description="An agent that can retrieve proteomics analysis results.",
   instruction=prompt.KRAKEN_MCP_PROMPT,
   tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="docker",
                    args=[
                        "run",
                        "-e",
                        f"MONGO_PORT={KRAKEN_PORT}",
                        "-e",
                        f"MONGO_HOST={KRAKEN_HOST}",
                        "-e",
                        f"MONGO_USER={KRAKEN_USER}",
                        "-e",
                        f"MONGO_PASSWORD={KRAKEN_PASSWORD}",
                        "--network", 
                        "host",
                        "-i", 
                        "--rm",
                        "mcpserver"
                    ]
                )
            )
        )
    ]
)