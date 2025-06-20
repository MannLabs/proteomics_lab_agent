# Similar to: https://github.com/bhancockio/adk-mcp-tutorial/
"""database agent that can write and retrieve meta data to ms raw files into a data base"""

import os
import sqlite3

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def create_database():
    # Check if the database already exists
    db_exists = os.path.exists(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if not db_exists:
        print(f"Creating new database at {DATABASE_PATH}...")
        
        # Create performance_data table (fixed table name and removed trailing comma)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                instrument TEXT NOT NULL,
                gradient REAL NOT NULL,
                performance_status BOOLEAN NOT NULL DEFAULT 0,
                comment TEXT
            )
            """
        )
        print("Created 'performance_data' table.")
        
        # Insert dummy data (added comment field and fixed data)
        first_entry = [
            ("20250611_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A3_1_21296.d", "tims2", 43.998, 1, ""),
            ("20250528_TIMS02_EVO05_LuHe_DIAMA_HeLa_200ng_44min_01_S6-H2_1_21203.d", "tims2", 43.998, 0, "High mass error for MS1 and MS2. TOF needs calibration.")
        ]
        cursor.executemany(
            "INSERT INTO performance_data (file_name, instrument, gradient, performance_status, comment) VALUES (?, ?, ?, ?, ?)",
            first_entry
        )
        print(f"Inserted {len(first_entry)} initial entry.")
        
        conn.commit()
        print("Database created and populated successfully.")
    else:
        print(f"Database already exists at {DATABASE_PATH}. No changes made.")
    
    conn.close()

if __name__ == "__main__":
    create_database()
