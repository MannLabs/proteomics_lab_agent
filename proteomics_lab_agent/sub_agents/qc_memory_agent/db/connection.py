"""qc_memory agent can store and retrieve past evaluations of proteomics analysis results into a database."""

from __future__ import annotations

import logging
import sqlite3
from typing import NoReturn

from proteomics_lab_agent.sub_agents.qc_memory_agent.db.utils import (
    COMPATIBLE_SCHEMA_VERSION,
    DATABASE_PATH,
    DatabaseError,
)

logger = logging.getLogger(__name__)


def _raise_schema_not_found_error() -> NoReturn:
    """Helper function to raise schema version not found error."""
    raise DatabaseError("Schema version table '_schema_version' not found or is empty.")


def _raise_schema_mismatch_error(db_version: int) -> NoReturn:
    """Helper function to raise schema mismatch error."""
    raise DatabaseError(
        f"Database schema version mismatch. Agent requires "
        f"version {COMPATIBLE_SCHEMA_VERSION}, but database is "
        f"version {db_version}."
    )


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection, validate schema version, and set row factory.

    Raises
    ------
    DatabaseError
        If connection fails or if schema version is incompatible.

    Returns
    -------
    sqlite3.Connection
        An active database connection.

    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.exception("Failed to connect to database.")
        raise DatabaseError(f"Database connection error: {e!s}") from e

    try:
        cursor = conn.cursor()
        # Fetch the highest (latest) schema version
        cursor.execute(
            "SELECT version FROM _schema_version ORDER BY version DESC LIMIT 1"
        )
        db_version_row = cursor.fetchone()

        if db_version_row is None:
            _raise_schema_not_found_error()

        db_version = db_version_row["version"]
        if db_version != COMPATIBLE_SCHEMA_VERSION:
            _raise_schema_mismatch_error(db_version)

    except sqlite3.Error as e:
        conn.close()
        logger.exception("Failed to validate database schema version.")
        if "no such table" in str(e):
            raise DatabaseError(
                "Schema version table '_schema_version' not found. "
                "Is this an old or uninitialized database?"
            ) from e
        raise DatabaseError(f"Schema check failed: {e!s}") from e
    except DatabaseError:
        conn.close()
        raise
    else:
        logger.debug(f"DB schema version {db_version} validated successfully.")
        return conn
