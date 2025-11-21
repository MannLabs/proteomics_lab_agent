"""Shared pytest fixtures for all tests."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


os.environ["ALPHAKRAKEN_MCP_URL"] = "http://localhost:8080/mcp"


@pytest.fixture
def in_memory_db() -> Generator[Path, None, None]:
    """Create an in-memory database with schema initialized.

    Yields
    ------
    Path
        Path to the in-memory database (actually a temporary file for testing).

    """
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp_file:
        db_path = Path(tmp_file.name)

    # Initialize the schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_data (
                id TEXT PRIMARY KEY,
                performance_status BOOLEAN NOT NULL DEFAULT 0,
                performance_rating REAL NOT NULL DEFAULT 0 CHECK (performance_rating >= 0 AND performance_rating <= 5),
                performance_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_agent_version TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                instrument_id TEXT NOT NULL,
                gradient REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_files_to_performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                performance_data_id TEXT NOT NULL,
                raw_files_id INTEGER NOT NULL,
                FOREIGN KEY (performance_data_id) REFERENCES performance_data (id) ON DELETE CASCADE,
                FOREIGN KEY (raw_files_id) REFERENCES raw_files (id) ON DELETE CASCADE,
                UNIQUE(performance_data_id, raw_files_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _schema_version (
                version INTEGER PRIMARY KEY,
                applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert schema version
        cursor.execute("INSERT INTO _schema_version (version) VALUES (?)", (1,))

        conn.commit()
    finally:
        conn.close()

    return db_path


@pytest.fixture
def mock_env_vars() -> dict[str, str]:
    """Provide mock environment variables for tests."""
    return {
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test-bucket/knowledge",
        "example_protocol1_path": "gs://test-bucket/protocol1.pdf",
        "example_video1_path": "gs://test-bucket/video1.mp4",
        "example_protocol2_path": "gs://test-bucket/protocol2.pdf",
        "example_video2_path": "gs://test-bucket/video2.mp4",
        "example_protocol_path": "gs://test-bucket/protocol.pdf",
        "example_video_path": "gs://test-bucket/video.mp4",
        "example_lab_note_path": "gs://test-bucket/lab_note.pdf",
    }
