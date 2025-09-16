"""qc_memory agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).parent / "database.db"
GRADIENT_TOLERANCE = (
    0.001  # Tolerance for retrieving raw files based on gradient length
)
MAX_PERFORMANCE_RATING = 5


class DatabaseError(Exception):
    """Custom exception for database operations."""


class ValidationError(DatabaseError):
    """Exception for data validation errors."""


class SessionError(DatabaseError):
    """Exception for session processing errors."""


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with row factory set to sqlite3.Row."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error as e:
        logger.exception("Failed to connect to database.")
        raise DatabaseError("Database connection failed.") from e
    else:
        return conn


def list_db_tables() -> dict:
    """Lists all tables in the SQLite database.

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool), 'message' (str), and 'data' containing the table names if successful.

    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

    except DatabaseError as e:
        logger.exception("Database error listing tables.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
            "data": {"tables": []},
        }
    except sqlite3.Error as e:
        logger.exception("Unexpected database error listing tables.")
        return {
            "success": False,
            "message": f"Unexpected error: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "data": {"tables": []},
        }
    else:
        logger.info(f"Successfully listed {len(tables)} tables")
        return {
            "success": True,
            "message": "Tables listed successfully.",
            "data": {"tables": tables},
        }


def get_table_schema(table_name: str) -> dict:
    """Gets the schema (column names and types) of a specific table.

    Parameters
    ----------
    table_name : str
        The name of the table to get schema for.

    Returns
    -------
    dict
        Dictionary with success status and schema information.

    """
    if not table_name or not isinstance(table_name, str):
        return {
            "success": False,
            "message": "table_name must be a non-empty string",
            "error_code": "VALIDATION_ERROR",
        }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            schema_info = cursor.fetchall()

        if not schema_info:
            return {
                "success": False,
                "message": f"Table '{table_name}' not found or no schema information.",
                "error_code": "TABLE_NOT_FOUND",
            }

        columns = [{"name": row["name"], "type": row["type"]} for row in schema_info]

    except DatabaseError as e:
        logger.exception(f"Database error getting schema for '{table_name}'.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    except sqlite3.Error as e:
        logger.exception(f"Unexpected error getting schema for '{table_name}'.")
        return {
            "success": False,
            "message": f"Unexpected error: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    else:
        logger.info(
            f"Successfully retrieved schema for table '{table_name}' with {len(columns)} columns"
        )
        return {
            "success": True,
            "message": f"Schema retrieved for table '{table_name}'.",
            "data": {"table_name": table_name, "columns": columns},
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
        return {
            "success": False,
            "message": "Invalid session data provided - must be a dictionary",
            "error_code": "VALIDATION_ERROR",
        }

    if not session_data.get("raw_files"):
        return {
            "success": False,
            "message": "No raw files provided in session data",
            "error_code": "VALIDATION_ERROR",
        }

    if not isinstance(session_data["raw_files"], list):
        return {
            "success": False,
            "message": "raw_files must be a list",
            "error_code": "VALIDATION_ERROR",
        }

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
            "error_code": "VALIDATION_ERROR",
        }

    # Validate performance_rating range
    rating = session_data.get("performance_rating")
    if not isinstance(rating, (int, float)) or not (
        0 <= rating <= MAX_PERFORMANCE_RATING
    ):
        return {
            "success": False,
            "message": f"performance_rating must be an integer between 0 and {MAX_PERFORMANCE_RATING}",
            "error_code": "VALIDATION_ERROR",
        }

    return {"success": True, "message": "Validation passed"}


def _normalize_file_instruments(raw_files: list) -> None:
    """Normalizes instrument names in the raw files data."""
    for file_data in raw_files:
        if "instrument_id" in file_data:
            file_data["instrument_id"] = InstrumentNormalizer.normalize(
                file_data["instrument_id"]
            )


def _insert_performance_record(session_data: dict, cursor: sqlite3.Cursor) -> int:
    """Inserts the performance data record and returns the performance ID."""
    perf_cols = [k for k in session_data if k != "raw_files"]
    perf_values = [session_data[k] for k in perf_cols]

    perf_query = f"""
        INSERT INTO performance_data ({", ".join(perf_cols)})
        VALUES ({", ".join(["?" for _ in perf_cols])})
    """

    cursor.execute(perf_query, perf_values)
    performance_id = cursor.lastrowid

    if not performance_id:
        raise DatabaseError("Failed to get performance_id after insert")

    return performance_id


def _get_or_create_raw_file(
    file_data: dict,
    conn: sqlite3.Connection | None = None,
    cursor: sqlite3.Cursor | None = None,
) -> dict:
    """Gets an existing raw file record or creates/updates one based on file data.

    Implements upsert logic that works with any SQLite version without requiring specific table constraints. If a file with the same name exists:
    - Returns the existing record if instrument_id and gradient match exactly
    - Updates the existing record if instrument_id or gradient differ
    - Creates a new record if no file with that name exists

    Parameters
    ----------
    file_data : dict
        Dictionary containing file information with required keys:
        - 'file_name' (str): The name of the file
        - 'instrument_id' (str): The instrument name
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
        cursor = conn.cursor()
    elif cursor is None:
        cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, instrument_id, gradient FROM raw_files WHERE file_name = ?",
            (file_data["file_name"],),
        )
        existing = cursor.fetchone()

        if existing:
            return _handle_existing_file(
                existing, file_data, cursor, conn, own_connection=own_connection
            )
        return _create_new_file(file_data, cursor, conn, own_connection=own_connection)

    except sqlite3.Error as e:
        if own_connection:
            conn.rollback()
        logger.exception(
            f"Database error processing file '{file_data.get('file_name', 'unknown')}'."
        )
        raise DatabaseError(
            f"Error processing file '{file_data.get('file_name', 'unknown')}': {e}"
        ) from e
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
    instrument_match = existing_instrument == file_data["instrument_id"]
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
        "UPDATE raw_files SET instrument_id = ?, gradient = ? WHERE id = ?",
        (file_data["instrument_id"], file_data["gradient"], existing_id),
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
        "INSERT INTO raw_files (file_name, instrument_id, gradient) VALUES (?, ?, ?)",
        (
            file_data["file_name"],
            file_data["instrument_id"],
            file_data["gradient"],
        ),
    )
    new_id = cursor.lastrowid

    if not new_id:
        raise DatabaseError("Failed to get file_id after insert")

    if own_connection:
        conn.commit()

    return {
        "success": True,
        "file_id": new_id,
        "action": "created",
        "message": f"Created new file: {file_data['file_name']}",
    }


def _raise_file_processing_error(message: str) -> None:
    """Helper function to raise file processing errors."""
    raise DatabaseError(message)


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

    # Process all files first to collect any errors
    for file_data in raw_files:
        file_result = _get_or_create_raw_file(file_data, conn, cursor)
        if file_result["success"]:
            file_ids.append(file_result["file_id"])
            file_actions.append(file_result["action"])
        else:
            _raise_file_processing_error(
                f"Failed to process file: {file_result['message']}"
            )

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


def _raise_file_processing_failure(message: str) -> None:
    """Helper function to raise file processing failure."""
    raise DatabaseError(message)


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
            - instrument_id (str): Instrument name
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
                "instrument_id": "tims2",
                "gradient": 43.998
            },
            {
                "file_name": "20250623_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A4_1_21403.d",
                "instrument_id": "tims2",
                "gradient": 43.998
            }
        ]
    }
    result = insert_performance_session(session_data)

    """
    try:
        validation_result = _validate_session_data(session_data)
        if not validation_result["success"]:
            logger.error(
                f"Session data validation failed: {validation_result['message']}"
            )
            return validation_result

        _normalize_file_instruments(session_data["raw_files"])

        with get_db_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            try:
                performance_id = _insert_performance_record(session_data, cursor)
                file_result = _process_raw_files(
                    session_data["raw_files"], conn, cursor
                )
                if not file_result["success"]:
                    _raise_file_processing_failure(
                        f"File processing failed: {file_result['message']}"
                    )

                links_created = _link_files_to_session(
                    performance_id, file_result["file_ids"], cursor
                )

                conn.commit()

                summary = _generate_session_summary(
                    file_result["file_ids"], file_result["file_actions"], links_created
                )

                result = {
                    "success": True,
                    "message": summary["summary_message"],
                    "data": {
                        "performance_id": performance_id,
                        "raw_file_ids": file_result["file_ids"],
                        "files_created": summary["files_created"],
                        "files_updated": summary["files_updated"],
                        "files_reused": summary["files_reused"],
                        "links_created": summary["links_created"],
                    },
                }

                logger.info(
                    f"Successfully created performance session {performance_id} with {len(file_result['file_ids'])} files"
                )

            except Exception:
                conn.rollback()
                raise

    except ValidationError as e:
        logger.exception("Validation error in insert_performance_session.")
        return {
            "success": False,
            "message": f"Validation error: {e!s}",
            "error_code": "VALIDATION_ERROR",
        }
    except DatabaseError as e:
        logger.exception("Database error in insert_performance_session.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    except sqlite3.Error as e:
        logger.exception("Unexpected database error in insert_performance_session.")
        return {
            "success": False,
            "message": f"Unexpected error during session creation: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    else:
        return result


def _validate_filters(filters: dict, filter_mappings: dict) -> dict:
    """Validate filter keys against allowed mappings."""
    if not filters:
        return {"success": True}

    if not isinstance(filters, dict):
        return {
            "success": False,
            "message": "Filters must be a dictionary",
            "error_code": "VALIDATION_ERROR",
        }

    invalid_filters = [key for key in filters if key not in filter_mappings]
    if invalid_filters:
        return {
            "success": False,
            "message": f"Invalid filter field(s): {invalid_filters}. Valid fields: {list(filter_mappings.keys())}",
            "error_code": "VALIDATION_ERROR",
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
                raise ValidationError(
                    "Invalid gradient filter format. Use 'min'/'max', 'tolerance'/'value', or numeric value."
                )
            return condition, params
        # Exact match (backward compatible)
        return f"{db_column} = ?", [value]

    # Exact match for other fields
    return f"{db_column} = ?", [value]


def query_performance_data(filters: dict) -> dict:
    """Queries the performance data with optional filters.

    Performs an inner join between performance_data and raw_files tables
    to retrieve both performance information and file details.

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
    try:
        filter_mappings = {
            "performance_status": "pd.performance_status",
            "performance_rating": "pd.performance_rating",
            "performance_comment": "pd.performance_comment",
            "instrument_id": "rf.instrument_id",
            "gradient": "rf.gradient",
            "file_name": "rf.file_name",
        }

        # Validate filters
        validation_result = _validate_filters(filters, filter_mappings)
        if not validation_result["success"]:
            logger.error(f"Filter validation failed: {validation_result['message']}")
            return validation_result

        with get_db_connection() as conn:
            cursor = conn.cursor()

            base_query = """
            SELECT
                rf.id,
                rf.file_name,
                rf.instrument_id,
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

            logger.info(
                f"Query returned {len(results)} records with filters: {filters}"
            )

    except ValidationError as e:
        logger.exception("Validation error in query_performance_data.")
        return {
            "success": False,
            "message": f"Validation error: {e!s}",
            "error_code": "VALIDATION_ERROR",
            "data": {"results": [], "count": 0},
        }
    except DatabaseError as e:
        logger.exception("Database error in query_performance_data.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
            "data": {"results": [], "count": 0},
        }
    except sqlite3.Error as e:
        logger.exception("Unexpected database error in query_performance_data.")
        return {
            "success": False,
            "message": f"Unexpected error querying performance data: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "data": {"results": [], "count": 0},
        }
    else:
        return {
            "success": True,
            "message": f"Query executed successfully. Found {len(results)} record(s).",
            "data": {"results": results, "count": len(results)},
        }
