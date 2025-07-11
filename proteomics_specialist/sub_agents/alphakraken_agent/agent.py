"""Alphakraken agent can retrieve proteomics analysis results."""

import logging

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

from .. import utils  # noqa: TID252
from . import prompt

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"  # "gemini-2.0-flash-001" might have lower latency.

try:
    KRAKEN_PORT = utils.get_required_env("KRAKEN_PORT")
    KRAKEN_HOST = utils.get_required_env("KRAKEN_HOST")
    KRAKEN_USER = utils.get_required_env("KRAKEN_USER")
    KRAKEN_PASSWORD = utils.get_required_env("KRAKEN_PASSWORD")
except ValueError:
    logger.exception("Configuration error occurred")

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
                        "mcpserver",
                    ],
                )
            )
        )
    ],
)
