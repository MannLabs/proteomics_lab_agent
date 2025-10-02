"""qc_memory agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import NoReturn

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


def _raise_performance_id_error() -> NoReturn:
    """Helper function to raise performance ID error."""
    raise DatabaseError("Failed to get performance_id after insert")


def _raise_file_id_error() -> NoReturn:
    """Helper function to raise file ID error."""
    raise DatabaseError("Failed to get file_id after insert")


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with row factory set to sqlite3.Row."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.exception("Failed to connect to database.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    else:
        return conn


def list_db_tables() -> dict:
    """Lists all tables in the SQLite database.

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool), 'message' (str),
        and 'data' containing the table names if successful.

    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        logger.info(f"Successfully listed {len(tables)} tables")
    except sqlite3.Error as e:
        logger.exception("Database error listing tables.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    except Exception as e:
        logger.exception("Unexpected error listing tables.")
        return {
            "success": False,
            "message": f"Unexpected error: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    else:
        return {
            "success": True,
            "message": "Tables listed successfully.",
            "data": {"tables": tables},
        }
    finally:
        conn.close()


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
        conn = get_db_connection()
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
        logger.info(
            "Successfully retrieved schema for table '%s' with %d columns",
            table_name,
            len(columns),
        )
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
        return {
            "success": True,
            "message": f"Schema retrieved for table '{table_name}'.",
            "data": {"table_name": table_name, "columns": columns},
        }
    finally:
        conn.close()


def _validate_query_filters(filters: dict) -> dict | None:
    """Validate query filters and return error dict if invalid, None if valid."""
    filter_mappings = {
        "performance_status": "pd.performance_status",
        "performance_rating": "pd.performance_rating",
        "performance_comment": "pd.performance_comment",
        "instrument_id": "rf.instrument_id",
        "gradient": "rf.gradient",
        "file_name": "rf.file_name",
    }

    if not filters:
        return {
            "success": False,
            "message": "No filter provided",
            "error_code": "VALIDATION_ERROR",
        }
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
    return None


def _build_gradient_condition(value: dict | float) -> tuple[str, list]:
    """Build gradient filter condition and parameters."""
    if isinstance(value, dict):
        # Handle gradient range queries
        if "min" in value and "max" in value:
            return "rf.gradient BETWEEN ? AND ?", [value["min"], value["max"]]
        if "min" in value:
            return "rf.gradient >= ?", [value["min"]]
        if "max" in value:
            return "rf.gradient <= ?", [value["max"]]
        if "tolerance" in value and "value" in value:
            target = value["value"]
            tolerance = value["tolerance"]
            return "rf.gradient BETWEEN ? AND ?", [
                target - tolerance,
                target + tolerance,
            ]
        raise ValidationError(
            "Invalid gradient filter format. Use 'min'/'max', 'tolerance'/'value', or numeric value."
        )
    # Exact match (backward compatible)
    return "rf.gradient = ?", [value]


def _build_filter_conditions(filters: dict) -> tuple[list, list]:
    """Build filter conditions and parameters for query."""
    filter_mappings = {
        "performance_status": "pd.performance_status",
        "performance_rating": "pd.performance_rating",
        "performance_comment": "pd.performance_comment",
        "instrument_id": "rf.instrument_id",
        "gradient": "rf.gradient",
        "file_name": "rf.file_name",
    }

    conditions = []
    params = []

    for field, value in filters.items():
        db_column = filter_mappings[field]

        if field == "performance_comment" and isinstance(value, str):
            condition = f"{db_column} LIKE ?"
            condition_params = [f"%{value}%"]
        elif field == "gradient":
            condition, condition_params = _build_gradient_condition(value)
        else:
            # Exact match for other fields
            condition = f"{db_column} = ?"
            condition_params = [value]

        conditions.append(condition)
        params.extend(condition_params)

    return conditions, params


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
    validation_error = _validate_query_filters(filters)
    if validation_error:
        return validation_error

    try:
        conn = get_db_connection()
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

        conditions, params = _build_filter_conditions(filters)

        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY pd.id, rf.id"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        logger.info(f"Query returned {len(results)} records with filters: {filters}")

    except ValidationError as e:
        logger.exception("Validation error in query_performance_data.")
        return {
            "success": False,
            "message": f"Validation error: {e!s}",
            "error_code": "VALIDATION_ERROR",
        }
    except DatabaseError as e:
        logger.exception("Database error in query_performance_data.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    except sqlite3.Error as e:
        logger.exception("Unexpected database error in query_performance_data.")
        return {
            "success": False,
            "message": f"Unexpected error querying performance data: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    except Exception as e:
        logger.exception("Unexpected error in query_performance_data.")
        return {
            "success": False,
            "message": f"Unexpected error: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    else:
        return {
            "success": True,
            "message": f"Query executed successfully. Found {len(results)} record(s).",
            "data": {"results": results, "count": len(results)},
        }
    finally:
        conn.close()


def _validate_session_structure(session_data: dict) -> dict | None:
    """Validate basic session data structure."""
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
    return None


def _validate_required_fields(session_data: dict) -> dict | None:
    """Validate required fields are present."""
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
    return None


def _validate_performance_fields(session_data: dict) -> dict | None:
    """Validate performance-related fields."""
    status_error = _validate_performance_status(session_data.get("performance_status"))
    if status_error:
        return status_error

    rating_error = _validate_performance_rating(session_data.get("performance_rating"))
    if rating_error:
        return rating_error

    return None


def _validate_session_data(session_data: dict) -> dict | None:
    """Validate session data and return error dict if invalid, None if valid."""
    structure_error = _validate_session_structure(session_data)
    if structure_error:
        return structure_error

    fields_error = _validate_required_fields(session_data)
    if fields_error:
        return fields_error

    performance_error = _validate_performance_fields(session_data)
    if performance_error:
        return performance_error

    files_error = _validate_raw_files(session_data["raw_files"])
    if files_error:
        return files_error

    return None


def _validate_performance_status(status: int) -> dict | None:
    """Validate performance status field."""
    if not isinstance(status, (int, bool)) or status not in (0, 1):
        return {
            "success": False,
            "message": "performance_status must be 0, 1",
            "error_code": "VALIDATION_ERROR",
        }
    return None


def _validate_performance_rating(rating: float) -> dict | None:
    """Validate performance rating field."""
    if not isinstance(rating, (int, float)) or not (
        0 <= rating <= MAX_PERFORMANCE_RATING
    ):
        return {
            "success": False,
            "message": f"performance_rating must be an integer or float between 0 and {MAX_PERFORMANCE_RATING}",
            "error_code": "VALIDATION_ERROR",
        }
    return None


def _validate_raw_files(raw_files: list) -> dict | None:
    """Validate raw files list."""
    for i, file_data in enumerate(raw_files):
        if not isinstance(file_data, dict):
            return {
                "success": False,
                "message": f"Raw file at index {i} must be a dictionary",
                "error_code": "VALIDATION_ERROR",
            }
        if isinstance(file_data["gradient"], str):
            try:
                file_data["gradient"] = float(file_data["gradient"])
            except ValueError as e:
                raise ValidationError(
                    f"Invalid gradient value: {file_data['gradient']}"
                ) from e

        required_file_fields = ["file_name", "instrument_id", "gradient"]
        missing_file_fields = [
            field for field in required_file_fields if field not in file_data
        ]
        if missing_file_fields:
            return {
                "success": False,
                "message": f"Raw file at index {i} missing required fields: {', '.join(missing_file_fields)}",
                "error_code": "VALIDATION_ERROR",
            }

        field_error = _validate_file_fields(file_data, i)
        if field_error:
            return field_error

    return None


def _validate_file_fields(file_data: dict, index: int) -> dict | None:
    """Validate individual file field values."""
    if (
        not isinstance(file_data["file_name"], str)
        or not file_data["file_name"].strip()
    ):
        return {
            "success": False,
            "message": f"Raw file at index {index}: file_name must be a non-empty string",
            "error_code": "VALIDATION_ERROR",
        }
    if (
        not isinstance(file_data["instrument_id"], str)
        or not file_data["instrument_id"].strip()
    ):
        return {
            "success": False,
            "message": f"Raw file at index {index}: instrument_id must be a non-empty string",
            "error_code": "VALIDATION_ERROR",
        }
    if not isinstance(file_data["gradient"], (int, float)):
        return {
            "success": False,
            "message": f"Raw file at index {index}: gradient must be a float or int",
            "error_code": "VALIDATION_ERROR",
        }
    return None


def _process_raw_file(cursor: sqlite3.Cursor, file_data: dict) -> tuple[int, str]:
    """Process a single raw file and return (file_id, action)."""
    cursor.execute(
        "SELECT id, instrument_id, gradient FROM raw_files WHERE file_name = ?",
        (file_data["file_name"],),
    )
    existing = cursor.fetchone()

    if existing:
        existing_id, existing_instrument, existing_gradient = existing

        instrument_match = existing_instrument == file_data["instrument_id"]
        gradient_diff = abs(existing_gradient - file_data["gradient"])
        gradient_match = gradient_diff < GRADIENT_TOLERANCE

        if instrument_match and gradient_match:
            return existing_id, "found_exact_match"
        # File exists but with different data - update it
        cursor.execute(
            "UPDATE raw_files SET instrument_id = ?, gradient = ? WHERE id = ?",
            (
                file_data["instrument_id"],
                file_data["gradient"],
                existing_id,
            ),
        )
        return existing_id, "updated"
    # Create new file record
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
        _raise_file_id_error()

    return new_id, "created"


def insert_performance_and_raw_file_info(session_data: dict) -> dict:
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
    result = insert_performance_and_raw_file_info(session_data)

    """
    validation_error = _validate_session_data(session_data)
    if validation_error:
        return validation_error

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert performance record
        perf_cols = [k for k in session_data if k != "raw_files"]
        perf_values = [session_data[k] for k in perf_cols]

        columns = ", ".join(perf_cols)
        placeholders = ", ".join(["?" for _ in perf_cols])
        perf_query = f"""
            INSERT INTO performance_data ({columns})
            VALUES ({placeholders})
        """

        cursor.execute(perf_query, perf_values)
        performance_id = cursor.lastrowid

        if not performance_id:
            _raise_performance_id_error()

        # Process raw files
        file_ids = []
        file_actions = []

        for file_data in session_data["raw_files"]:
            file_id, action = _process_raw_file(cursor, file_data)
            file_ids.append(file_id)
            file_actions.append(action)

        # Insert links between session data and raw file info
        link_query = """
            INSERT OR IGNORE INTO raw_file_to_session (performance_id, raw_file_id)
            VALUES (?, ?)
        """

        link_data = [(performance_id, file_id) for file_id in file_ids]
        cursor.executemany(link_query, link_data)
        links_created = cursor.rowcount

        conn.commit()

        # Generate session summary
        created_count = file_actions.count("created")
        updated_count = file_actions.count("updated")
        found_count = file_actions.count("found_exact_match")

        summary_message = f"Session created with {len(file_ids)} files ({created_count} new, {updated_count} updated, {found_count} reused)"
        logger.info(
            f"Successfully created performance session {performance_id} with {len(file_ids)} files"
        )

    except sqlite3.Error as e:
        conn.rollback()  # Roll back changes on error
        return {
            "success": False,
            "message": f"Unexpected error during session creation: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    except ValidationError as e:
        logger.exception("Validation error in insert_performance_and_raw_file_info.")
        return {
            "success": False,
            "message": f"Validation error: {e!s}",
            "error_code": "VALIDATION_ERROR",
        }
    except DatabaseError as e:
        logger.exception("Database error in insert_performance_and_raw_file_info.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    except Exception as e:
        logger.exception("Unexpected error in insert_performance_and_raw_file_info.")
        return {
            "success": False,
            "message": f"Unexpected error: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
        }
    else:
        return {
            "success": True,
            "message": summary_message,
            "data": {
                "performance_id": performance_id,
                "raw_file_ids": file_ids,
                "files_created": created_count,
                "files_updated": updated_count,
                "files_reused": found_count,
                "links_created": links_created,
            },
        }
    finally:
        conn.close()
