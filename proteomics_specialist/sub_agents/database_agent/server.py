"""Database agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import ClassVar

# MCP Server Imports
import mcp.server.stdio
from dotenv import load_dotenv

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

GRADIENT_TOLERANCE = 0.001

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
# --- End Logging Setup ---

DATABASE_PATH = Path(__file__).parent / "database.db"


# --- Database Utility Functions ---
def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with row factory set to sqlite3.Row."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_db_tables() -> dict:
    """Lists all tables in the SQLite database.

    Parameters
    ----------
    None

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool), 'message' (str), and 'tables' (list[str]) containing the table names if successful.

    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
    except sqlite3.Error as e:
        return {"success": False, "message": f"Error listing tables: {e}", "tables": []}
    else:
        return {
            "success": True,
            "message": "Tables listed successfully.",
            "tables": tables,
        }


def get_table_schema(table_name: str) -> dict:
    """Gets the schema (column names and types) of a specific table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}');")
    schema_info = cursor.fetchall()
    conn.close()
    if not schema_info:
        raise ValueError(f"Table '{table_name}' not found or no schema information.")

    columns = [{"name": row["name"], "type": row["type"]} for row in schema_info]
    return {"table_name": table_name, "columns": columns}


def query_db_table(table_name: str, columns: str, condition: str) -> list[dict]:
    """Queries a table with an optional condition.

    Parameters
    ----------
    table_name : str
        The name of the table to query.
    columns : str, optional
        Comma-separated list of columns to retrieve (e.g., "id, name"), default is "*".
    condition : str, optional
        Optional SQL WHERE clause condition (e.g., "id = 1" or "completed = 0").

    Returns
    -------
    list[dict]
        A list of dictionaries, where each dictionary represents a row.

    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT {columns} FROM {table_name}"
    if condition:
        query += f" WHERE {condition}"
    query += ";"

    try:
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        conn.close()
        raise ValueError(f"Error querying table '{table_name}': {e}") from None
    conn.close()
    return results


def insert_data(table_name: str, data: dict) -> dict:
    """Inserts a new row of data into the specified table.

    Parameters
    ----------
    table_name : str
        The name of the table to insert data into.
    data : dict
        A dictionary where keys are column names and values are the corresponding values for the new row.

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool) and 'message' (str). If successful, 'message' includes the ID of the newly inserted row.

    """
    if not data:
        return {"success": False, "message": "No data provided for insertion."}

    conn = get_db_connection()
    cursor = conn.cursor()

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    values = tuple(data.values())

    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    try:
        cursor.execute(query, values)
        conn.commit()
        last_row_id = cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"Error inserting data into table '{table_name}': {e}",
        }
    else:
        return {
            "success": True,
            "message": f"Data inserted successfully. Row ID: {last_row_id}",
            "row_id": last_row_id,
        }
    finally:
        conn.close()


def insert_many_data(table_name: str, rows_data: list[dict]) -> dict:
    """Inserts multiple rows into a specified SQLite table in a single transaction.

    Parameters
    ----------
    table_name : str
        The name of the table to insert data into.
    rows_data : list[dict]
        A list of dictionaries, where each dictionary represents a row to be inserted.

    Returns
    -------
    dict
        A result dictionary with success status, a message, and a list of the newly created row IDs.

    """
    if not rows_data:
        return {
            "success": False,
            "row_ids": [],
            "message": "No data provided for insertion.",
        }

    columns = ", ".join(rows_data[0].keys())
    placeholders = ", ".join(["?" for _ in rows_data[0]])
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    values_list = [tuple(row.values()) for row in rows_data]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT MAX(id) FROM {table_name}")
        max_id_result = cursor.fetchone()
        current_max_id = max_id_result[0] if max_id_result[0] is not None else 0

        cursor.executemany(query, values_list)
        num_inserted = cursor.rowcount
        first_id = current_max_id + 1
        last_id = current_max_id + num_inserted
        inserted_ids = list(range(first_id, last_id + 1))

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"Error batch inserting data into table '{table_name}': {e}",
        }
    else:
        return {
            "success": True,
            "message": f"{num_inserted} rows inserted successfully into {table_name}.",
            "row_ids": inserted_ids,
        }
    finally:
        conn.close()


def get_or_create_raw_file_expert(file_data: dict) -> dict:
    """Gets an existing raw file record or creates/updates one based on file data.

    Implements upsert logic that works with any SQLite version without requiring specific table constraints. If a file with the same name exists:
    - Returns the existing record if instrument and gradient match exactly
    - Updates the existing record if instrument or gradient differ
    - Creates a new record if no file with that name exists

    Parameters
    ----------
    file_data : dict
        Dictionary containing file information with required keys:
        - 'file_name' (str): The name of the file
        - 'instrument' (str): The instrument name
        - 'gradient' (float): The gradient value

    Returns
    -------
    dict
        Result with success status, file_id, action ('found_exact_match', 'updated', or 'created') and message.

    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, instrument, gradient FROM raw_files WHERE file_name = ?",
            (file_data["file_name"],),
        )
        existing = cursor.fetchone()

        if existing:
            existing_id, existing_instrument, existing_gradient = existing

            # Check if the existing file matches exactly
            if (
                existing_instrument == file_data["instrument"]
                and abs(existing_gradient - file_data["gradient"]) < GRADIENT_TOLERANCE
            ):
                return {
                    "success": True,
                    "file_id": existing_id,
                    "action": "found_exact_match",
                    "message": f"Using existing file: {file_data['file_name']}",
                }
            # File exists but with different data - update it
            cursor.execute(
                "UPDATE raw_files SET instrument = ?, gradient = ? WHERE id = ?",
                (file_data["instrument"], file_data["gradient"], existing_id),
            )
            conn.commit()
            return {
                "success": True,
                "file_id": existing_id,
                "action": "updated",
                "message": f"Updated existing file: {file_data['file_name']}",
            }
        # File doesn't exist - create it
        cursor.execute(
            "INSERT INTO raw_files (file_name, instrument, gradient) VALUES (?, ?, ?)",
            (
                file_data["file_name"],
                file_data["instrument"],
                file_data["gradient"],
            ),
        )
        conn.commit()
        return {
            "success": True,
            "file_id": cursor.lastrowid,
            "action": "created",
            "message": f"Created new file: {file_data['file_name']}",
        }

    except sqlite3.Error as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"Error processing file '{file_data.get('file_name', 'unknown')}': {e}",
        }
    finally:
        conn.close()


class InstrumentNormalizer:
    """Pattern-based instrument name normalization."""

    VALID_INSTRUMENTS: ClassVar[set[str]] = {
        "astral1",
        "astral2",
        "astral3",
        "astral4",
        "tims1",
        "tims2",
        "tims3",
        "tims5",
        "eclipse1",
        "zeno1",
        "zeno2",
        "stellar1",
    }

    @classmethod
    def normalize(cls, instrument: str) -> str:
        """Normalize instrument name to standard form."""
        if not instrument:
            return instrument

        cleaned = instrument.lower().strip()

        # Matches: name + optional separator + optional leading zero + number
        match = re.match(r"^(astral|tims|eclipse|zeno|stellar)[-_]?0?(\d+)$", cleaned)
        if match:
            instrument_type, number = match.groups()
            normalized = f"{instrument_type}{number}"

            if normalized in cls.VALID_INSTRUMENTS:
                return normalized

        return cleaned

    @classmethod
    def get_valid_instruments(cls) -> set:
        """Get set of known valid instruments."""
        return cls.VALID_INSTRUMENTS.copy()


def insert_performance_session(session_data: dict) -> dict:
    """Inserts a complete performance session with files in a single function call.

    Parameters
    ----------
    session_data : dict
        Dictionary containing:
        - performance_status (boolean): Performance status (0 or 1). 0: Not ready for measurment, 1: measured
        - performance_rating (int): Performance rating on a scale 0-5. 0: not rated, 1: very bad, 2: bad, 3: neutral, 4: good, 5: very good.
        - performance_comment (str): Performance comment
        - raw_files (list): List of file dictionaries, each with:
            - file_name (str): Filename
            - instrument (str): Instrument name
            - gradient (float): Gradient value

    Returns
    -------
    dict
        Result with success status, message, and all inserted IDs

    Examples
    --------
    session_data = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "Excellent performance",
        "raw_files": [
            {
                "file_name": "20250623_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A3_1_21402.d",
                "instrument": "tims2",
                "gradient": 43.998
            },
            {
                "file_name": "20250623_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A4_1_21403.d",
                "instrument": "tims2",
                "gradient": 43.998
            }
        ]
    }
    result = insert_performance_session(session_data)

    """
    if not session_data or not session_data.get("raw_files"):
        return {"success": False, "message": "Invalid session data provided"}

    for file_data in session_data["raw_files"]:
        if "instrument" in file_data:
            file_data["instrument"] = InstrumentNormalizer.normalize(
                file_data["instrument"]
            )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute("BEGIN IMMEDIATE")

        perf_cols = [k for k in session_data if k != "raw_files"]
        perf_values = [session_data[k] for k in perf_cols]

        perf_query = f"""
            INSERT INTO performance_data ({", ".join(perf_cols)})
            VALUES ({", ".join(["?" for _ in perf_cols])})
        """

        cursor.execute(perf_query, perf_values)
        performance_id = cursor.lastrowid

        conn.commit()

        file_ids = []
        file_actions = []

        for file_data in session_data["raw_files"]:
            file_result = get_or_create_raw_file_expert(file_data)
            if file_result["success"]:
                file_ids.append(file_result["file_id"])
                file_actions.append(file_result["action"])
            else:
                return {
                    "success": False,
                    "message": f"Failed to process file: {file_result['message']}",
                }

        conn.execute("BEGIN IMMEDIATE")

        link_query = """
            INSERT OR IGNORE INTO raw_file_to_session (performance_id, raw_file_id)
            VALUES (?, ?)
        """

        link_data = [(performance_id, file_id) for file_id in file_ids]
        cursor.executemany(link_query, link_data)
        links_created = cursor.rowcount

        conn.commit()

        created_count = file_actions.count("created")
        updated_count = file_actions.count("updated")
        found_count = file_actions.count("found_exact_match")

        return {
            "success": True,
            "message": f"Session created with {len(file_ids)} files ({created_count} new, {updated_count} updated, {found_count} reused)",
            "performance_id": performance_id,
            "raw_file_ids": file_ids,
            "files_created": created_count,
            "files_updated": updated_count,
            "files_reused": found_count,
            "links_created": links_created,
        }

    except sqlite3.Error as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"Database error during session creation: {e}",
        }
    finally:
        conn.close()


def _validate_filters(filters: dict, filter_mappings: dict) -> dict:
    """Validate filter keys against allowed mappings."""
    if not filters:
        return {"success": True}

    invalid_filters = [key for key in filters if key not in filter_mappings]
    if invalid_filters:
        return {
            "success": False,
            "message": f"Invalid filter field(s): {invalid_filters}. Valid fields: {list(filter_mappings.keys())}",
            "data": [],
        }
    return {"success": True}


def _build_gradient_condition(value: dict, db_column: str) -> tuple:
    """Build gradient filter condition and parameters."""
    if "min" in value and "max" in value:
        return f"{db_column} BETWEEN ? AND ?", [value["min"], value["max"]]

    if "min" in value:
        return f"{db_column} >= ?", [value["min"]]

    if "max" in value:
        return f"{db_column} <= ?", [value["max"]]

    if "tolerance" in value and "value" in value:
        target = value["value"]
        tolerance = value["tolerance"]
        return f"{db_column} BETWEEN ? AND ?", [target - tolerance, target + tolerance]

    return None, None


def _build_filter_condition(
    field: str, value: str | float | bool | dict, db_column: str
) -> tuple:
    """Build filter condition and parameters for a single field."""
    if field == "performance_comment" and isinstance(value, str):
        return f"{db_column} LIKE ?", [f"%{value}%"]

    if field == "gradient":
        if isinstance(value, dict):
            condition, params = _build_gradient_condition(value, db_column)
            if condition is None:
                raise ValueError(
                    "Invalid gradient filter format. Use 'min'/'max', 'tolerance'/'value', or numeric value."
                )
            return condition, params
        # Exact match (backward compatible)
        return f"{db_column} = ?", [value]

    # Exact match for other fields
    return f"{db_column} = ?", [value]


def query_performance_data(filters: dict) -> dict:
    """Queries performance data with optional filters across joined tables.

    Parameters
    ----------
    filters : dict
        A dictionary where keys are filter field names and values are the corresponding filter values. Valid keys are:
        - 'performance_status': Boolean (0,1)
        - 'performance_rating': Integer (0-5)
        - 'performance_comment': String (partial match)
        - 'instrument': String (exact match)
        - 'gradient': Float (exact match) OR dict with range options
        - 'file_name': String (exact match)

        For gradient range queries, use:
        - 'gradient': {'min': 40.0, 'max': 45.0} # Range query
        - 'gradient': {'min': 40.0} # Greater than or equal
        - 'gradient': {'max': 45.0} # Less than or equal
        - 'gradient': {'tolerance': 0.5, 'value': 44.0} # Within tolerance
        - 'gradient': 44.0 # Exact match (backward compatible)

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool), 'message' (str), and 'data' (list). If successful, 'data' contains a list of dictionaries with performance info.

    """
    filter_mappings = {
        "performance_status": "pd.performance_status",
        "performance_rating": "pd.performance_rating",
        "performance_comment": "pd.performance_comment",
        "instrument": "rf.instrument",
        "gradient": "rf.gradient",
        "file_name": "rf.file_name",
    }

    validation_result = _validate_filters(filters, filter_mappings)
    if not validation_result["success"]:
        return validation_result

    conn = get_db_connection()
    cursor = conn.cursor()

    base_query = """
    SELECT
        rf.id,
        rf.file_name,
        rf.instrument,
        rf.gradient,
        pd.performance_status,
        pd.performance_rating,
        pd.performance_comment
    FROM raw_files rf
    JOIN raw_file_to_session rfts ON rf.id = rfts.raw_file_id
    JOIN performance_data pd ON rfts.performance_id = pd.id
    """

    conditions = []
    params = []

    try:
        for field, value in filters.items():
            db_column = filter_mappings[field]
            condition, condition_params = _build_filter_condition(
                field, value, db_column
            )
            conditions.append(condition)
            params.extend(condition_params)

        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY pd.id, rf.id"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        return {
            "success": True,
            "message": f"Query executed successfully. Found {len(results)} record(s).",
            "data": results,
        }

    except ValueError as e:
        return {
            "success": False,
            "message": str(e),
            "data": [],
        }
    except sqlite3.Error as e:
        return {
            "success": False,
            "message": f"Error querying performance data: {e}",
            "data": [],
        }
    finally:
        conn.close()


def delete_data(table_name: str, condition: str) -> dict:
    """Deletes rows from a table based on a given SQL WHERE clause condition.

    Parameters
    ----------
    table_name : str
        The name of the table to delete data from.
    condition : str
        The SQL WHERE clause condition to specify which rows to delete. This condition MUST NOT be empty to prevent accidental mass deletion.

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool) and 'message' (str). If successful, 'message' includes the count of deleted rows.

    """
    if not condition or not condition.strip():
        return {
            "success": False,
            "message": "Deletion condition cannot be empty. This is a safety measure to prevent accidental deletion of all rows.",
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"DELETE FROM {table_name} WHERE {condition}"

    try:
        cursor.execute(query)
        rows_deleted = cursor.rowcount
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"Error deleting data from table '{table_name}': {e}",
        }
    else:
        return {
            "success": True,
            "message": f"{rows_deleted} row(s) deleted successfully from table '{table_name}'.",
            "rows_deleted": rows_deleted,
        }
    finally:
        conn.close()


# --- MCP Server Setup ---
logging.info("Creating MCP Server instance for SQLite DB...")
app = Server("sqlite-db-mcp-server")

# Wrap database utility functions as ADK FunctionTools
ADK_DB_TOOLS = {
    "list_db_tables": FunctionTool(func=list_db_tables),
    "get_table_schema": FunctionTool(func=get_table_schema),
    # "query_db_table": FunctionTool(func=query_db_table),
    # "insert_data": FunctionTool(func=insert_data),
    # "delete_data": FunctionTool(func=delete_data),
    "query_performance_data": FunctionTool(func=query_performance_data),
    "insert_performance_session": FunctionTool(func=insert_performance_session),
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
