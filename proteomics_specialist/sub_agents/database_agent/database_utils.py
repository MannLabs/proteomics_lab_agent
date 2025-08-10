"""Database agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import ClassVar

DATABASE_PATH = Path(__file__).parent / "database.db"
GRADIENT_TOLERANCE = (
    0.001  # Tolerance for retrieving raw files based on gradient length
)


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
    if not table_name or not isinstance(table_name, str):
        return {"success": False, "message": "Invalid table name provided."}

    if not data or not isinstance(data, dict):
        return {"success": False, "message": "No data provided for insertion."}

    if not data:
        return {"success": False, "message": "Data dictionary is empty."}

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


def _get_or_create_raw_file(
    file_data: dict,
    conn: sqlite3.Connection | None = None,
    cursor: sqlite3.Cursor | None = None,
) -> dict:
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
    conn : Optional[sqlite3.Connection], optional
        Existing database connection. If None, creates a new one.
    cursor : Optional[sqlite3.Cursor], optional
        Existing database cursor. If None, creates from conn.

    Returns
    -------
    dict
        Result with success status, file_id, action ('found_exact_match', 'updated', or 'created') and message.

    """
    # Use provided connection or create new one
    own_connection = conn is None
    if own_connection:
        conn = get_db_connection()
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
    elif cursor is None:
        cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, instrument, gradient FROM raw_files WHERE file_name = ?",
            (file_data["file_name"],),
        )
        existing = cursor.fetchone()

        if existing:
            return _handle_existing_file(
                existing, file_data, cursor, conn, own_connection
            )
        return _create_new_file(file_data, cursor, conn, own_connection)

    except sqlite3.Error as e:
        if own_connection:
            conn.rollback()
        return {
            "success": False,
            "message": f"Error processing file '{file_data.get('file_name', 'unknown')}': {e}",
        }
    finally:
        if own_connection:
            conn.close()


def _handle_existing_file(
    existing: tuple,
    file_data: dict,
    cursor: sqlite3.Cursor,
    conn: sqlite3.Connection,
    *,
    own_connection: bool,
) -> dict:
    """Handle logic for existing file."""
    existing_id, existing_instrument, existing_gradient = existing

    # Check if the existing file matches exactly
    instrument_match = existing_instrument == file_data["instrument"]
    gradient_diff = abs(existing_gradient - file_data["gradient"])
    gradient_match = gradient_diff < GRADIENT_TOLERANCE

    if instrument_match and gradient_match:
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

    if own_connection:
        conn.commit()

    return {
        "success": True,
        "file_id": existing_id,
        "action": "updated",
        "message": f"Updated existing file: {file_data['file_name']}",
    }


def _create_new_file(
    file_data: dict,
    cursor: sqlite3.Cursor,
    conn: sqlite3.Connection,
    *,
    own_connection: bool,
) -> dict:
    """Create a new file record."""
    cursor.execute(
        "INSERT INTO raw_files (file_name, instrument, gradient) VALUES (?, ?, ?)",
        (
            file_data["file_name"],
            file_data["instrument"],
            file_data["gradient"],
        ),
    )
    new_id = cursor.lastrowid

    if own_connection:
        conn.commit()

    return {
        "success": True,
        "file_id": new_id,
        "action": "created",
        "message": f"Created new file: {file_data['file_name']}",
    }


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


def _validate_session_data(session_data: dict) -> dict:
    """Validates the session data structure and required fields."""
    if not session_data or not isinstance(session_data, dict):
        return {"success": False, "message": "Invalid session data provided"}

    if not session_data.get("raw_files"):
        return {"success": False, "message": "No raw files provided in session data"}

    if not isinstance(session_data["raw_files"], list):
        return {"success": False, "message": "raw_files must be a list"}

    required_fields = [
        "performance_status",
        "performance_rating",
        "performance_comment",
    ]
    missing_fields = [field for field in required_fields if field not in session_data]
    if missing_fields:
        return {
            "success": False,
            "message": f"Missing required fields: {', '.join(missing_fields)}",
        }

    return {"success": True, "message": "Validation passed"}


def _normalize_file_instruments(raw_files: list) -> None:
    """Normalizes instrument names in the raw files data."""
    for file_data in raw_files:
        if "instrument" in file_data:
            file_data["instrument"] = InstrumentNormalizer.normalize(
                file_data["instrument"]
            )


def _insert_performance_record(session_data: dict, cursor: sqlite3.Cursor) -> int:
    """Inserts the performance data record and returns the performance ID.

    Parameters
    ----------
    session_data : dict
        Session data containing performance information
    cursor : sqlite3.Cursor
        Database cursor for executing queries

    Returns
    -------
    int
        The ID of the newly inserted performance record

    """
    perf_cols = [k for k in session_data if k != "raw_files"]
    perf_values = [session_data[k] for k in perf_cols]

    perf_query = f"""
        INSERT INTO performance_data ({", ".join(perf_cols)})
        VALUES ({", ".join(["?" for _ in perf_cols])})
    """

    cursor.execute(perf_query, perf_values)
    return cursor.lastrowid


def _process_raw_files(
    raw_files: list,
    conn: sqlite3.Connection | None = None,
    cursor: sqlite3.Cursor | None = None,
) -> dict:
    """Processes all raw files and returns their IDs and processing results.

    Parameters
    ----------
    raw_files : list
        List of raw file data dictionaries
    conn : Optional[sqlite3.Connection], optional
        Database connection to use
    cursor : Optional[sqlite3.Cursor], optional
        Database cursor to use

    Returns
    -------
    dict
        Processing result containing file IDs, actions, and success status

    """
    file_ids = []
    file_actions = []

    for file_data in raw_files:
        file_result = _get_or_create_raw_file(file_data, conn, cursor)
        if file_result["success"]:
            file_ids.append(file_result["file_id"])
            file_actions.append(file_result["action"])
        else:
            return {
                "success": False,
                "message": f"Failed to process file: {file_result['message']}",
                "file_ids": [],
                "file_actions": [],
            }

    return {
        "success": True,
        "message": "All files processed successfully",
        "file_ids": file_ids,
        "file_actions": file_actions,
    }


def _link_files_to_session(
    performance_id: int, file_ids: list, cursor: sqlite3.Cursor
) -> int:
    """Links raw files to the performance session.

    Parameters
    ----------
    performance_id : int
        The performance session ID
    file_ids : list
        List of raw file IDs to link
    cursor : sqlite3.Cursor
        Database cursor for executing queries

    Returns
    -------
    int
        Number of links created

    """
    link_query = """
        INSERT OR IGNORE INTO raw_file_to_session (performance_id, raw_file_id)
        VALUES (?, ?)
    """

    link_data = [(performance_id, file_id) for file_id in file_ids]
    cursor.executemany(link_query, link_data)
    return cursor.rowcount


def _generate_session_summary(
    file_ids: list, file_actions: list, links_created: int
) -> dict:
    """Generates a summary of the session creation results.

    Parameters
    ----------
    file_ids : list
        List of processed file IDs
    file_actions : list
        List of actions taken for each file
    links_created : int
        Number of file-session links created

    Returns
    -------
    dict
        Summary statistics of the session creation

    """
    created_count = file_actions.count("created")
    updated_count = file_actions.count("updated")
    found_count = file_actions.count("found_exact_match")

    return {
        "total_files": len(file_ids),
        "files_created": created_count,
        "files_updated": updated_count,
        "files_reused": found_count,
        "links_created": links_created,
        "summary_message": f"Session created with {len(file_ids)} files ({created_count} new, {updated_count} updated, {found_count} reused)",
    }


class SessionError(Exception):
    """Exception raised for session processing errors."""


def insert_performance_session(session_data: dict) -> dict:
    """Inserts a complete performance session with files in a single function call.

    Parameters
    ----------
    session_data : dict
        Dictionary containing:
        - performance_status (boolean): Performance status (0 or 1). 0: Not ready for measurement, 1: measured
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
    validation_result = _validate_session_data(session_data)
    if not validation_result["success"]:
        return validation_result

    _normalize_file_instruments(session_data["raw_files"])
    conn = get_db_connection()
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        conn.execute("BEGIN IMMEDIATE")
        performance_id = _insert_performance_record(session_data, cursor)

        file_result = _process_raw_files(session_data["raw_files"], conn, cursor)
        if not file_result["success"]:
            raise SessionError(f"File processing failed: {file_result['message']}")  # noqa: TRY301

        links_created = _link_files_to_session(
            performance_id, file_result["file_ids"], cursor
        )

        conn.commit()

        summary = _generate_session_summary(
            file_result["file_ids"], file_result["file_actions"], links_created
        )

        return {
            "success": True,
            "message": summary["summary_message"],
            "performance_id": performance_id,
            "raw_file_ids": file_result["file_ids"],
            "files_created": summary["files_created"],
            "files_updated": summary["files_updated"],
            "files_reused": summary["files_reused"],
            "links_created": summary["links_created"],
        }

    except (sqlite3.Error, SessionError) as e:
        conn.rollback()
        error_type = "Database" if isinstance(e, sqlite3.Error) else "Session"
        return {
            "success": False,
            "message": f"{error_type} error during session creation: {e}",
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


def _build_gradient_condition(
    value: dict, db_column: str
) -> tuple[str | None, list | None]:
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
