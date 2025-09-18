"""qc_memory agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from pathlib import Path

import database_utils
import mcp.server.stdio
from dotenv import load_dotenv
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

load_dotenv()

LOG_FILE_PATH = Path(__file__).parent / "mcp_server_activity.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode="a"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# --- MCP Server Setup ---
logger.info("Creating MCP Server instance for SQLite DB...")
app = Server("sqlite-db-mcp-server")

# Wrap database utility functions as ADK FunctionTools
ADK_DB_TOOLS = {
    "list_db_tables": FunctionTool(func=database_utils.list_db_tables),
    "get_table_schema": FunctionTool(func=database_utils.get_table_schema),
    "query_performance_data": FunctionTool(func=database_utils.query_performance_data),
    "insert_performance_and_raw_file_info": FunctionTool(
        func=database_utils.insert_performance_and_raw_file_info
    ),
}


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logger.info("MCP Server: Received list_tools request")
    mcp_tools_list = []

    try:
        for tool_name, adk_tool_instance in ADK_DB_TOOLS.items():
            if not adk_tool_instance.name:
                adk_tool_instance.name = tool_name

            mcp_tool_schema = adk_to_mcp_tool_type(adk_tool_instance)
            logger.info(f"MCP Server: Advertising tool: {mcp_tool_schema.name}")
            mcp_tools_list.append(mcp_tool_schema)
        logger.info(f"MCP Server: Successfully listed {len(mcp_tools_list)} tools")
    except Exception:
        logger.exception("Error listing tools")
        return {
            "success": False,
            "message": "Empty list of MCP tools",
            "error_code": "LIST_MCP_ERROR",
        }
    else:
        return mcp_tools_list


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logger.info(f"MCP Server: Executing tool '{name}' with args: {arguments}")

    if name not in ADK_DB_TOOLS:
        error_message = f"Tool '{name}' not implemented by this server. Available tools: {list(ADK_DB_TOOLS.keys())}"
        logger.warning(error_message)
        error_payload = {
            "success": False,
            "message": error_message,
            "error_code": "TOOL_NOT_FOUND",
            "available_tools": list(ADK_DB_TOOLS.keys()),
        }
        return [
            mcp_types.TextContent(type="text", text=json.dumps(error_payload, indent=2))
        ]

    try:
        adk_tool_instance = ADK_DB_TOOLS[name]

        # Execute the tool
        adk_tool_response = await adk_tool_instance.run_async(
            args=arguments,
            tool_context=None,
        )

        # The response should already be properly formatted by safe_execute_db_function
        if not isinstance(adk_tool_response, dict):
            logger.error(
                f"Tool '{name}' wrapper returned non-dict: {type(adk_tool_response)}"
            )
            error_payload = {
                "success": False,
                "message": f"Tool '{name}' returned invalid response type: {type(adk_tool_response)}",
                "error_code": "INVALID_RESPONSE_TYPE",
                "tool_name": name,
            }
            return [
                mcp_types.TextContent(
                    type="text", text=json.dumps(error_payload, indent=2)
                )
            ]

        # Add metadata to response
        adk_tool_response["tool_name"] = name
        adk_tool_response["server_version"] = "0.2.0"

        # Final success/failure logging
        success = adk_tool_response.get("success", False)
        if success:
            logger.info(f"MCP Server: Tool '{name}' executed successfully")
        else:
            error_code = adk_tool_response.get("error_code", "UNKNOWN")
            logger.error(f"MCP Server: Tool '{name}' failed with code {error_code}")

        response_text = json.dumps(adk_tool_response, indent=2, default=str)
        logger.debug(
            f"MCP Server: Tool '{name}' response size: {len(response_text)} characters"
        )

        return [mcp_types.TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.exception(f"MCP Server: Unexpected error executing tool '{name}'")
        error_payload = {
            "success": False,
            "message": f"Unexpected error executing tool '{name}': {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "error_type": type(e).__name__,
            "tool_name": name,
            "traceback": traceback.format_exc(),
        }
        return [
            mcp_types.TextContent(type="text", text=json.dumps(error_payload, indent=2))
        ]


# --- MCP Server Runner ---
async def run_mcp_stdio_server() -> None:
    """Runs the MCP server, listening for connections over standard input/output."""
    logger.info("Starting database interaction")
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("MCP Stdio Server: Starting handshake with client...")
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=app.name,
                    server_version="0.2.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
            logger.info("MCP Stdio Server: Run loop finished or client disconnected")

    except Exception:
        logger.exception("Error in MCP stdio server")
        raise


if __name__ == "__main__":
    logger.info("Launching SQLite DB MCP Server via stdio...")
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        logger.info("MCP Server (stdio) stopped by user")
    except (OSError, RuntimeError, ValueError) as e:
        logger.info(f"MCP Server (stdio) encountered fatal error: {e}.", exc_info=True)
        raise
    finally:
        logger.info("MCP Server (stdio) process exiting")
