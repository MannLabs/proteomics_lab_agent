"""Unit tests for qc_memory_agent db_interface module."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import connection

# ============================================================================
# Tests for get_db_connection
# ============================================================================


def test_get_db_connection_returns_valid_connection(in_memory_db: Path) -> None:
    """Test that get_db_connection returns a valid connection with correct schema."""
    # given
    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        # when
        conn = connection.get_db_connection()

        # then
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

        # Verify we can query the database
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM _schema_version")
        version = cursor.fetchone()["version"]
        assert version == 1

        conn.close()


def test_get_db_connection_validates_schema_version(in_memory_db: Path) -> None:
    """Test that get_db_connection validates schema version matches expected version."""
    # given
    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        # when
        conn = connection.get_db_connection()

        # then
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version FROM _schema_version ORDER BY version DESC LIMIT 1"
        )
        db_version = cursor.fetchone()["version"]
        assert db_version == connection.COMPATIBLE_SCHEMA_VERSION
        conn.close()


def test_get_db_connection_raises_error_when_schema_table_missing() -> None:
    """Test that get_db_connection raises DatabaseError when _schema_version table doesn't exist."""
    # given
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = Path(tmp_file.name)

    # Create database without schema table
    conn = sqlite3.connect(db_path)
    conn.close()

    # when / then
    with (
        patch.object(connection, "DATABASE_PATH", db_path),
        pytest.raises(
            connection.DatabaseError,
            match="Schema version table '_schema_version' not found",
        ),
    ):
        connection.get_db_connection()

    # Cleanup
    db_path.unlink(missing_ok=True)


def test_get_db_connection_raises_error_when_schema_version_incompatible() -> None:
    """Test that get_db_connection raises DatabaseError when schema version doesn't match."""
    # given
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = Path(tmp_file.name)

    # Create database with incompatible schema version
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE _schema_version (version INTEGER PRIMARY KEY, applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cursor.execute("INSERT INTO _schema_version (version) VALUES (?)", (999,))
    conn.commit()
    conn.close()

    # when / then
    with (
        patch.object(connection, "DATABASE_PATH", db_path),
        pytest.raises(
            connection.DatabaseError,
            match=r"Database schema version mismatch.*requires version 1.*database is version 999",
        ),
    ):
        connection.get_db_connection()

    # Cleanup
    db_path.unlink(missing_ok=True)
