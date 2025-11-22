"""Database query functions for QC Memory Agent."""

import logging
import sqlite3

from proteomics_lab_agent.sub_agents.qc_memory_agent.db.connection import (
    get_db_connection,
)
from proteomics_lab_agent.sub_agents.qc_memory_agent.db.utils import (
    DatabaseError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _validate_query_filters(filters: dict) -> dict | None:
    """Validate query filters and return error dict if invalid, None if valid."""
    filter_mappings = {
        "performance_status": "pd.performance_status",
        "performance_rating": "pd.performance_rating",
        "performance_comment": "pd.performance_comment",
        "instrument_id": "rf.instrument_id",
        "gradient": "rf.gradient",
        "file_name": "rf.file_name",
        "created_by_agent_version": "pd.created_by_agent_version",
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
        "created_by_agent_version": "pd.created_by_agent_version",
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
        - 'instrument_id': String (exact match)
        - 'gradient': Float (exact match) OR dict with range options
        - 'file_name': String (exact match)
        - 'created_by_agent_version': String (exact match)

        For gradient range queries, use:
        - 'gradient': {'min': 40.0, 'max': 45.0} # Range query
        - 'gradient': {'min': 40.0} # Greater than or equal
        - 'gradient': {'max': 45.0} # Less than or equal
        - 'gradient': {'value': 44.0, 'tolerance': 0.1} # Within 10% tolerance
        - 'gradient': 44.0 # Exact match (backward compatible)

    Returns
    -------
    dict
        A dictionary with keys 'success' (bool), 'message' (str), and 'data' (list). If successful, 'data' contains a list of dictionaries with performance info.

    """
    validation_error = _validate_query_filters(filters)
    if validation_error:
        return validation_error

    conn = None
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
                pd.performance_comment,
                pd.created_by_agent_version
            FROM raw_files rf
            JOIN raw_files_to_performance_data rfts ON rf.id = rfts.raw_files_id
            JOIN performance_data pd ON rfts.performance_data_id = pd.id
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
    except (sqlite3.Error, DatabaseError) as e:
        logger.exception("Database error in query_performance_data.")
        return {
            "success": False,
            "message": f"Database error: {e!s}",
            "error_code": "DATABASE_ERROR",
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
        if conn:
            conn.close()
