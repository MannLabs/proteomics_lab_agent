"""database agent can store and retrieve past evaluations of proteomics analysis results into a database."""

import os
import sqlite3

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def create_database():
    db_exists = os.path.exists(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if not db_exists:
        print(f"Creating new database at {DATABASE_PATH}...")
    
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                performance_status BOOLEAN NOT NULL DEFAULT 0,
                performance_rating INTEGER NOT NULL DEFAULT 0 CHECK (performance_rating >= 0 AND performance_rating <= 5),
                performance_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created 'performance_data' table.")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                instrument TEXT NOT NULL,
                gradient REAL NOT NULL
            )
        """)
        print("Created 'raw_files' table.")
        
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
        print("Created 'raw_file_to_session' junction table.")
        
        sessions = [
            (1, 4, "good performance"),
            (0, 0, "High mass error for MS1 and MS2. TOF needs calibration."),
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO performance_data (performance_status, performance_rating, performance_comment)
            VALUES (?, ?, ?)
        """, sessions)
        print(f"Inserted {len(sessions)} performance sessions.")
        
        raw_files_data = [
            ("20250611_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A3_1_21296.d", "tims2", 43.998),
            ("20250528_TIMS02_EVO05_LuHe_DIAMA_HeLa_200ng_44min_01_S6-H2_1_21203.d", "tims2", 43.998),
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO raw_files (file_name, instrument, gradient)
            VALUES (?, ?, ?)
        """, raw_files_data)
        print(f"Inserted {len(raw_files_data)} raw files.")
        
        # Link sessions to files (many-to-many relationships)
        raw_files_to_session_data = [
            (1, 1),
            (2, 2),
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO raw_file_to_session (performance_id, raw_file_id)
            VALUES (?, ?)
        """, raw_files_to_session_data)
        print(f"Inserted {len(raw_files_to_session_data)} file-to-session links.")
        
        conn.commit()
        print("Database created and populated successfully.")
    else:
        print(f"Database already exists at {DATABASE_PATH}. No changes made.")
    
    conn.close()

if __name__ == "__main__":
    create_database()
