"""instrument agent can retrieve proteomics analysis results."""

import logging
import os

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from proteomics_specialist.config import config

from . import prompt

load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)

try:
    ALPHAKRAKEN_MCP_URL = os.getenv("ALPHAKRAKEN_MCP_URL")

except ValueError:
    logger.exception("Configuration error occurred")

instrument_agent = Agent(
    name="instrument_agent",
    model=config.model,
    description="An agent that can retrieve proteomics analysis results.",
    instruction=prompt.KRAKEN_MCP_PROMPT,
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPServerParams(
                url=ALPHAKRAKEN_MCP_URL,
            ),
        )
    ],
)
