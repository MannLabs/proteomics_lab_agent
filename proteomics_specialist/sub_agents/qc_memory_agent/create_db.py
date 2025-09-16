"""Database Schema Documentation.

============================

This module creates and initializes database for performance evaluations of analysis results.

Database Structure:
------------------

1. performance_data
   - Primary table storing performance sessions
   - Each record represents one performance evaluation session
   - Fields:
     * id: Unique identifier (PRIMARY KEY)
     * performance_status: Boolean (0=not ready, 1=measured)
     * performance_rating: Integer 0-5 (0=not rated, 1=very bad, 5=very good)
     * performance_comment: Text description of performance
     * created_at: Timestamp when record was created

2. raw_files
   - Stores information about raw data files
   - Each file is unique by filename
   - Fields:
     * id: Unique identifier (PRIMARY KEY)
     * file_name: Unique filename (UNIQUE constraint)
     * instrument_id: Instrument used (e.g., 'tims2')
     * gradient: Gradient time in minutes

3. raw_file_to_session (Junction Table)
   - Links performance sessions to raw files (many-to-many relationship)
   - Fields:
     * id: Unique identifier (PRIMARY KEY)
     * performance_id: Foreign key to performance_data.id
     * raw_file_id: Foreign key to raw_files.id
     * UNIQUE constraint on (performance_id, raw_file_id) prevents duplicates

Relationships:
-------------
performance_data (1) ←→ (M) raw_file_to_session (M) ←→ (1) raw_files

- One performance session can be linked to multiple raw files
- One raw file can be associated with multiple performance sessions
- CASCADE DELETE: Deleting a performance session or raw file removes all links.

"""

import logging
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
DATABASE_PATH = Path(__file__).parent / "database.db"


def create_database() -> None:
    """Create the database and initialize tables if it doesn't exist.

    This function:
    1. Creates the database file if it doesn't exist
    2. Creates three tables: performance_data, raw_files, raw_file_to_session
    3. Populates tables with sample data for testing
    4. Sets up foreign key relationships and constraints
    """
    db_exists = DATABASE_PATH.exists()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if not db_exists:
        logging.info(f"Creating new database at {DATABASE_PATH}...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                performance_status BOOLEAN NOT NULL DEFAULT 0,
                performance_rating REAL NOT NULL DEFAULT 0 CHECK (performance_rating >= 0 AND performance_rating <= 5),
                performance_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            CREATE TABLE IF NOT EXISTS raw_file_to_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                performance_id INTEGER NOT NULL,
                raw_file_id INTEGER NOT NULL,
                FOREIGN KEY (performance_id) REFERENCES performance_data (id) ON DELETE CASCADE,
                FOREIGN KEY (raw_file_id) REFERENCES raw_files (id) ON DELETE CASCADE,
                UNIQUE(performance_id, raw_file_id)
            )
        """)
        logging.info("Created 'raw_file_to_session' junction table.")

        sessions = [
            (1, 4, "good performance"),
            (0, 0, "High mass error for MS1 and MS2. TOF needs calibration."),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO performance_data (performance_status, performance_rating, performance_comment)
            VALUES (?, ?, ?)
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
            INSERT OR IGNORE INTO raw_files (file_name, instrument, gradient)
            VALUES (?, ?, ?)
            """,
            raw_files_data,
        )
        logging.info(f"Inserted {len(raw_files_data)} raw files.")

        # Link sessions to files (many-to-many relationships)
        raw_files_to_session_data = [
            (1, 1),
            (2, 2),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO raw_file_to_session (performance_id, raw_file_id)
            VALUES (?, ?)
            """,
            raw_files_to_session_data,
        )
        logging.info(
            f"Inserted {len(raw_files_to_session_data)} file-to-session links."
        )

        conn.commit()
        logging.info("Database created and populated successfully.")
    else:
        logging.info(f"Database already exists at {DATABASE_PATH}. No changes made.")

    conn.close()


if __name__ == "__main__":
    create_database()
