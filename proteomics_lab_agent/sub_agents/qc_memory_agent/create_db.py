"""Database Schema Documentation.

============================

This module creates and initializes database for performance evaluations of analysis results.

Database Structure:
------------------

1. performance_data
   - Primary table storing performance sessions
   - Each record represents one performance evaluation session
   - Fields:
     * id: Unique UUID identifier (PRIMARY KEY)
     * performance_status: Boolean (0=not ready, 1=measured)
     * performance_rating: Integer 0-5 (0=not rated, 1=very bad, 5=very good)
     * performance_comment: Text description of performance
     * created_at: Timestamp when record was created
     * created_by_agent_version: Text (Provenance: tracks which agent version created the record)

2. raw_files
   - Stores information about raw data files
   - Each file is unique by filename
   - Fields:
     * id: Unique identifier (PRIMARY KEY)
     * file_name: Unique filename (UNIQUE constraint)
     * instrument_id: Instrument used (e.g., 'tims2')
     * gradient: Gradient time in minutes

3. raw_files_to_performance_data (Junction Table)
   - Links performance sessions to raw files (many-to-many relationship)
   - Fields:
     * id: Unique identifier (PRIMARY KEY)
     * performance_data_id: Foreign key to performance_data.id
     * raw_files_id: Foreign key to raw_files.id
     * UNIQUE constraint on (performance_data_id, raw_files_id) prevents duplicates

4. _schema_version
   - Tracks the database schema version for agent compatibility
   - Fields:
     * version: Integer (PRIMARY KEY)
     * applied_on: Timestamp when this version was applied

Relationships:
-------------
performance_data (1) ←→ (M) raw_files_to_performance_data (M) ←→ (1) raw_files

- One performance session can be linked to multiple raw files
- One raw file can be associated with multiple performance sessions

Rationale for Data Strategy
---------------------------
1. Minimal Redundancy & Schema Decoupling:
   We intentionally store only the minimal subset of metadata (file_name, instrument_id,
   and gradient) required to uniquely identify a QC analysis. We strictly avoid
   duplicating computed metrics; this maintains the AlphaKraken database as the
   "Single Source of Truth" for quantitative data and ensures that future updates to
   AlphaKraken's schema do not break the integrity of our expert rating history.

2. Agent-Driven Consistency:
   The QC Memory Agent acts as the exclusive write-gateway to this database. By
   programmatically retrieving identifiers from the active AlphaKraken instance when
   recording a rating, the agent guarantees that shared metadata remains identical
   across both systems, preventing data drift.

3. Usage:
   To reconstruct the full analytical context, the "Expert Decisions" stored here
   (subjective ratings) must be joined with the "Performance Metrics" stored in
   AlphaKraken (objective data) using the unique `file_name`.
"""

import logging
import sqlite3
import uuid
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
DATABASE_PATH = Path(__file__).parent / "database.db"
SCHEMA_VERSION = 1


def create_database() -> None:
    """Create the database and initialize tables if it doesn't exist.

    This function:
    1. Creates the database file if it doesn't exist
    2. Creates four tables: performance_data, raw_files, raw_files_to_performance_data, _schema_version
    3. Populates tables with sample data for testing
    4. Sets up foreign key relationships and constraints
    """
    db_exists = DATABASE_PATH.exists()

    if db_exists:
        logging.warning(f"Database already exists at {DATABASE_PATH}.")
        logging.warning("Please delete the file 'database.db' to create a new one.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        logging.info(f"Creating new database at {DATABASE_PATH}...")

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
        logging.info("Created 'performance_data' table.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                instrument_id TEXT NOT NULL,
                gradient REAL NOT NULL
            )
        """)
        logging.info("Created 'raw_files' table.")

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
        logging.info("Created 'raw_files_to_performance_data' junction table.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _schema_version (
                version INTEGER PRIMARY KEY,
                applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "INSERT INTO _schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
        )
        logging.info(f"Created and set schema version to {SCHEMA_VERSION}.")

        session_uuid_1 = str(uuid.uuid4())
        session_uuid_2 = str(uuid.uuid4())

        sessions = [
            (session_uuid_1, 1, 4, "good performance", "db_init_v1"),
            (
                session_uuid_2,
                0,
                0,
                "High mass error for MS1 and MS2. TOF needs calibration.",
                "db_init_v1",
            ),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO performance_data
                (id, performance_status, performance_rating, performance_comment, created_by_agent_version)
            VALUES (?, ?, ?, ?, ?)
            """,
            sessions,
        )
        logging.info(f"Inserted {len(sessions)} performance sessions.")

        raw_files_data = [
            (
                "20250611_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A3_1_21296.d",
                "tims2",
                43.998,
            ),
            (
                "20250528_TIMS02_EVO05_LuHe_DIAMA_HeLa_200ng_44min_01_S6-H2_1_21203.d",
                "tims2",
                43.998,
            ),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO raw_files (file_name, instrument_id, gradient)
            VALUES (?, ?, ?)
            """,
            raw_files_data,
        )
        logging.info(f"Inserted {len(raw_files_data)} raw files.")

        # Link sessions to files (many-to-many relationships)
        raw_files_to_session_data = [
            (session_uuid_1, 1),
            (session_uuid_2, 2),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO raw_files_to_performance_data (performance_data_id, raw_files_id)
            VALUES (?, ?)
            """,
            raw_files_to_session_data,
        )
        logging.info(
            f"Inserted {len(raw_files_to_session_data)} file-to-session links."
        )

        conn.commit()
        logging.info("Database created and populated successfully.")

    except sqlite3.Error:
        logging.exception("An error occurred.")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    create_database()
