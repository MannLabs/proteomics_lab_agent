"""Unit tests for create_db module."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import create_db


def test_create_database_creates_all_tables_and_sample_data(tmp_path: Path) -> None:
    """Test that create_database creates all tables and populates with sample data."""
    # given
    test_db_path = tmp_path / "test_database.db"

    with patch.object(create_db, "DATABASE_PATH", test_db_path):
        # when
        create_db.create_database()

        # then
        assert test_db_path.exists()

        # Verify all tables exist and have correct structure
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check performance_data table exists and has sample data
        cursor.execute(
            "SELECT id, performance_status, performance_rating, performance_comment, created_by_agent_version FROM performance_data ORDER BY performance_status DESC"
        )
        perf_rows = [dict(row) for row in cursor.fetchall()]
        assert len(perf_rows) == 2

        # Verify first performance session (status=1)
        perf_1 = perf_rows[0]
        assert perf_1["performance_status"] == 1
        assert perf_1["performance_rating"] == 4.0
        assert perf_1["performance_comment"] == "good performance"
        assert perf_1["created_by_agent_version"] == "db_init_v1"
        assert isinstance(perf_1["id"], str)

        # Verify second performance session (status=0)
        perf_2 = perf_rows[1]
        assert perf_2["performance_status"] == 0
        assert perf_2["performance_rating"] == 0.0
        assert (
            perf_2["performance_comment"]
            == "High mass error for MS1 and MS2. TOF needs calibration."
        )
        assert perf_2["created_by_agent_version"] == "db_init_v1"
        assert isinstance(perf_2["id"], str)

        # Check raw_files table exists and has sample data
        cursor.execute("SELECT * FROM raw_files ORDER BY id")
        file_rows = [dict(row) for row in cursor.fetchall()]
        assert file_rows == [
            {
                "id": 1,
                "file_name": "20250611_TIMS02_EVO05_PaSk_DIAMA_HeLa_200ng_44min_S1-A3_1_21296.d",
                "instrument_id": "tims2",
                "gradient": 43.998,
            },
            {
                "id": 2,
                "file_name": "20250528_TIMS02_EVO05_LuHe_DIAMA_HeLa_200ng_44min_01_S6-H2_1_21203.d",
                "instrument_id": "tims2",
                "gradient": 43.998,
            },
        ]

        # Check junction table exists and has links
        cursor.execute(
            "SELECT id, performance_data_id, raw_files_id FROM raw_files_to_performance_data ORDER BY id"
        )
        link_rows = [dict(row) for row in cursor.fetchall()]
        assert len(link_rows) == 2
        assert link_rows[0]["id"] == 1
        assert link_rows[0]["performance_data_id"] == perf_1["id"]
        assert link_rows[0]["raw_files_id"] == 1
        assert link_rows[1]["id"] == 2
        assert link_rows[1]["performance_data_id"] == perf_2["id"]
        assert link_rows[1]["raw_files_id"] == 2

        # Check schema version table
        cursor.execute("SELECT version FROM _schema_version")
        schema_row = dict(cursor.fetchone())
        assert schema_row == {"version": 1}

        conn.close()
