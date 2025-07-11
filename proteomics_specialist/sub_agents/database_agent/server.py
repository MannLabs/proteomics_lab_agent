"""Database agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import asyncio
import json
import logging
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

# --- Logging Setup ---
LOG_FILE_PATH = Path(__file__).parent / "mcp_server_activity.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode="w"),
    ],
)
# # --- End Logging Setup ---

# DATABASE_PATH = Path(__file__).parent / "database.db"

# def get_db_connection() -> sqlite3.Connection:
#     """Get a database connection with row factory set to sqlite3.Row."""
#     conn = sqlite3.connect(DATABASE_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn


# --- MCP Server Setup ---
logging.info("Creating MCP Server instance for SQLite DB...")
app = Server("sqlite-db-mcp-server")

# Wrap database utility functions as ADK FunctionTools
ADK_DB_TOOLS = {
    "list_db_tables": FunctionTool(func=database_utils.list_db_tables),
    "get_table_schema": FunctionTool(func=database_utils.get_table_schema),
    # "query_db_table": FunctionTool(func=database_utils.query_db_table),
    # "insert_data": FunctionTool(func=database_utils.insert_data),
    # "delete_data": FunctionTool(func=database_utils.delete_data),
    "query_performance_data": FunctionTool(func=database_utils.query_performance_data),
    "insert_performance_session": FunctionTool(
        func=database_utils.insert_performance_session
    ),
}


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logging.info("MCP Server: Received list_tools request.")
    mcp_tools_list = []
    for tool_name, adk_tool_instance in ADK_DB_TOOLS.items():
        if not adk_tool_instance.name:
            adk_tool_instance.name = tool_name

        mcp_tool_schema = adk_to_mcp_tool_type(adk_tool_instance)
        logging.info(
            f"MCP Server: Advertising tool: {mcp_tool_schema.name}, InputSchema: {mcp_tool_schema.inputSchema}"
        )
        mcp_tools_list.append(mcp_tool_schema)
    return mcp_tools_list


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logging.info(
        f"MCP Server: Received call_tool request for '{name}' with args: {arguments}"
    )

    if name in ADK_DB_TOOLS:
        adk_tool_instance = ADK_DB_TOOLS[name]
        try:
            adk_tool_response = await adk_tool_instance.run_async(
                args=arguments,
                tool_context=None,
            )
            logging.info(
                f"MCP Server: ADK tool '{name}' executed. Response: {adk_tool_response}"
            )
            response_text = json.dumps(adk_tool_response, indent=2)
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            logging.exception(f"MCP Server: Error executing ADK tool '{name}'")
            error_payload = {
                "success": False,
                "message": f"Failed to execute tool '{name}': {e!s}",
            }
            error_text = json.dumps(error_payload)
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        logging.warning(f"MCP Server: Tool '{name}' not found/exposed by this server.")
        error_payload = {
            "success": False,
            "message": f"Tool '{name}' not implemented by this server.",
        }
        error_text = json.dumps(error_payload)
        return [mcp_types.TextContent(type="text", text=error_text)]


# --- MCP Server Runner ---
async def run_mcp_stdio_server() -> None:
    """Runs the MCP server, listening for connections over standard input/output."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logging.info("MCP Stdio Server: Starting handshake with client...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        logging.info("MCP Stdio Server: Run loop finished or client disconnected.")


if __name__ == "__main__":
    logging.info("Launching SQLite DB MCP Server via stdio...")
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        logging.info("\n MCP Server (stdio) stopped by user.")
    except (OSError, RuntimeError, ValueError) as e:
        logging.critical(
            f"MCP Server (stdio) encountered an unhandled error: {e}", exc_info=True
        )
    finally:
        logging.info("MCP Server (stdio) process exiting.")
