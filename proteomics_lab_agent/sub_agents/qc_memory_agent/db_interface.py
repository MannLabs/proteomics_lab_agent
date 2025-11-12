"""qc_memory agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import NoReturn

from proteomics_lab_agent.sub_agents.qc_memory_agent.db.connection import (
    get_db_connection,
)
from proteomics_lab_agent.sub_agents.qc_memory_agent.db.utils import (
    AGENT_NAME,
    GRADIENT_TOLERANCE,
    MAX_PERFORMANCE_RATING,
    DatabaseError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _raise_file_id_error() -> NoReturn:
    """Helper function to raise file ID error."""
    raise DatabaseError("Failed to get file_id after insert")


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
    if not isinstance(status, (int | bool)) or status not in (0, 1):
        return {
            "success": False,
            "message": "performance_status must be 0, 1",
            "error_code": "VALIDATION_ERROR",
        }
    return None


def _validate_performance_rating(rating: float) -> dict | None:
    """Validate performance rating field."""
    if not isinstance(rating, (int | float)) or not (
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

        # Check for required fields first
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

        # Attempt to convert string gradient to float
        if isinstance(file_data["gradient"], str):
            try:
                file_data["gradient"] = float(file_data["gradient"])
            except ValueError:
                return {
                    "success": False,
                    "message": f"Raw file at index {i}: gradient value '{file_data['gradient']}' cannot be converted to float",
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
    if not isinstance(file_data["gradient"], (int | float)):
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

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        performance_data_id = str(uuid.uuid4())

        # Insert performance record
        perf_cols = [k for k in session_data if k != "raw_files"]
        perf_values = [session_data[k] for k in perf_cols]

        perf_cols.insert(0, "id")
        perf_values.insert(0, performance_data_id)

        perf_cols.append("created_by_agent_version")
        perf_values.append(AGENT_NAME)

        columns = ", ".join(perf_cols)
        placeholders = ", ".join(["?" for _ in perf_cols])
        perf_query = f"""
            INSERT INTO performance_data ({columns})
            VALUES ({placeholders})
        """

        cursor.execute(perf_query, perf_values)

        # Process raw files
        file_ids = []
        file_actions = []

        for file_data in session_data["raw_files"]:
            file_id, action = _process_raw_file(cursor, file_data)
            file_ids.append(file_id)
            file_actions.append(action)

        # Insert links between session data and raw file info
        link_query = """
            INSERT OR IGNORE INTO raw_files_to_performance_data (performance_data_id, raw_files_id)
            VALUES (?, ?)
        """

        link_data = [(performance_data_id, file_id) for file_id in file_ids]
        cursor.executemany(link_query, link_data)
        links_created = cursor.rowcount

        conn.commit()

        # Generate session summary
        created_count = file_actions.count("created")
        updated_count = file_actions.count("updated")
        found_count = file_actions.count("found_exact_match")

        summary_message = f"Session created with {len(file_ids)} files ({created_count} new, {updated_count} updated, {found_count} reused)"
        logger.info(
            f"Successfully created performance session {performance_data_id} with {len(file_ids)} files"
        )

    except (sqlite3.Error, DatabaseError) as e:
        if conn:
            conn.rollback()  # Roll back changes on error
        return {
            "success": False,
            "message": f"Database error during session creation: {e!s}",
            "error_code": "DATABASE_ERROR",
        }
    except ValidationError as e:
        logger.exception("Validation error in insert_performance_and_raw_file_info.")
        return {
            "success": False,
            "message": f"Validation error: {e!s}",
            "error_code": "VALIDATION_ERROR",
        }
    except Exception as e:
        if conn:
            conn.rollback()
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
                "performance_data_id": performance_data_id,
                "raw_files_ids": file_ids,
                "files_created": created_count,
                "files_updated": updated_count,
                "files_reused": found_count,
                "links_created": links_created,
            },
        }
    finally:
        if conn:
            conn.close()
