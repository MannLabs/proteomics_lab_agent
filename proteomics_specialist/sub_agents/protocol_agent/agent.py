"""protocol agent that can retrieve protocols"""
# Used following MCP server: https://github.com/sooperset/mcp-atlassian

import os

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters

from . import prompt

MODEL = "gemini-2.0-flash-001"

CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

protocol_agent = Agent(
   name="protocol_agent",
   model=MODEL,
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
                        "-e", "CONFLUENCE_URL",
                        "-e", "CONFLUENCE_USERNAME",
                        "-e", "CONFLUENCE_API_TOKEN",
                        "-e", "MCP_VERBOSE",
                        "-e", "MCP_LOGGING_STDOUT",
                        "-e", "READ_ONLY_MODE",
                        "-e", "CONFLUENCE_SPACES_FILTER",
                        "ghcr.io/sooperset/mcp-atlassian:latest",
                    ],
                    env= {
                        "CONFLUENCE_URL": CONFLUENCE_URL,
                        "CONFLUENCE_USERNAME": CONFLUENCE_USERNAME,
                        "CONFLUENCE_API_TOKEN": CONFLUENCE_API_TOKEN,
                        "MCP_VERBOSE": "true",
                        "MCP_LOGGING_STDOUT": "true",
                        "READ_ONLY_MODE": "true",
                        "CONFLUENCE_SPACES_FILTER": "ProtocolMCP"
                    }
                )
            )
        )
    ]
)