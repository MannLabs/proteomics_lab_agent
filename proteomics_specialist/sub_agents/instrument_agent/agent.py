"""instrument agent can retrieve proteomics analysis results."""

import logging

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from proteomics_lab_agent.config import config
from proteomics_lab_agent.sub_agents.enviroment_handling import get_env_var

from . import prompt

load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)

try:
    ALPHAKRAKEN_MCP_URL = get_env_var("ALPHAKRAKEN_MCP_URL")
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
