"""Protocol agent can retrieve protocols from Confluence."""
# Uses following MCP server: https://github.com/sooperset/mcp-atlassian

import logging

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

from proteomics_specialist.config import config

from .. import utils  # noqa: TID252
from . import prompt

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"  # "gemini-2.0-flash-001" might have lower latency.

try:
    CONFLUENCE_URL = utils.get_required_env("CONFLUENCE_URL")
    CONFLUENCE_USERNAME = utils.get_required_env("CONFLUENCE_USERNAME")
    CONFLUENCE_API_TOKEN = utils.get_required_env("CONFLUENCE_API_TOKEN")
except ValueError:
    logger.exception("Configuration error occurred")

protocol_agent = Agent(
    name="protocol_agent",
    model=config.model,
    description="Agent to search and create protocols in our Confluence database.",
    instruction=prompt.PROTOCOL_PROMPT,
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="docker",
                    args=[
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        "CONFLUENCE_URL",
                        "-e",
                        "CONFLUENCE_USERNAME",
                        "-e",
                        "CONFLUENCE_API_TOKEN",
                        "-e",
                        "MCP_VERBOSE",
                        "-e",
                        "MCP_LOGGING_STDOUT",
                        "-e",
                        "ENABLED_TOOLS",
                        "-e",
                        "CONFLUENCE_SPACES_FILTER",
                        "ghcr.io/sooperset/mcp-atlassian:latest",
                    ],
                    env={
                        "CONFLUENCE_URL": CONFLUENCE_URL,
                        "CONFLUENCE_USERNAME": CONFLUENCE_USERNAME,
                        "CONFLUENCE_API_TOKEN": CONFLUENCE_API_TOKEN,
                        "MCP_VERBOSE": "true",
                        "MCP_LOGGING_STDOUT": "true",
                        # "READ_ONLY_MODE": "true",
                        "CONFLUENCE_SPACES_FILTER": "ProtocolMCP",
                        "ENABLED_TOOLS": "confluence_search,confluence_get_page,confluence_get_page_children,confluence_get_labels,confluence_create_page,confluence_update_page,confluence_add_label",
                    },
                )
            )
        )
    ],
)
