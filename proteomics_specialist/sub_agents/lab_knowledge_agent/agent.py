"""lab_knowledge agent  can retrieve protocols from Confluence."""
# Uses following MCP server: https://github.com/sooperset/mcp-atlassian

import logging

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from proteomics_specialist.config import config
from proteomics_specialist.sub_agents.enviroment_handling import get_env_var

from . import prompt

logger = logging.getLogger(__name__)

load_dotenv(".env.secrets")

try:
    CONFLUENCE_MCP_URL = get_env_var("CONFLUENCE_MCP_URL")
except ValueError:
    logger.exception("Configuration error occurred")

lab_knowledge_agent = Agent(
    name="lab_knowledge_agent",
    model=config.model,
    description="Agent to search and create protocols in our Confluence database.",
    instruction=prompt.PROTOCOL_PROMPT,
    tools=[
        MCPToolset(
            # https://google.github.io/adk-docs/tools/mcp-tools/#pattern-2-remote-mcp-servers-streamable-http
            # https://github.com/sooperset/mcp-atlassian?tab=readme-ov-file#-http-transport-configuration
            # IMPORTANT: use StreamableHTTPServerParams rather than StreamableHTTPConnectionParams
            connection_params=StreamableHTTPServerParams(
                url=CONFLUENCE_MCP_URL,
            ),
        )
    ],
    output_key="retrieved_protocol",
)
