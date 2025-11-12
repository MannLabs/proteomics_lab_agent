"""Unit tests for qc_memory_agent insert module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import connection, insert

# ============================================================================
# Tests for _validate_session_structure
# ============================================================================


def test_validate_session_structure_returns_none_for_valid_structure() -> None:
    """Test that _validate_session_structure returns None for valid session data."""
    # given
    session_data = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "Good",
        "raw_files": [
            {"file_name": "test.d", "instrument_id": "tims1", "gradient": 44.0}
        ],
    }

    # when
    result = insert._validate_session_structure(session_data)

    # then
    assert result is None


def test_validate_session_structure_returns_error_for_none() -> None:
    """Test that _validate_session_structure returns error dict when session_data is None."""
    # given
    session_data = None

    # when
    result = insert._validate_session_structure(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Invalid session data provided - must be a dictionary",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_structure_returns_error_for_non_dict() -> None:
    """Test that _validate_session_structure returns error dict when session_data is not dict."""
    # given
    session_data = ["not", "a", "dict"]

    # when
    result = insert._validate_session_structure(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Invalid session data provided - must be a dictionary",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_structure_returns_error_when_raw_files_missing() -> None:
    """Test that _validate_session_structure returns error dict when raw_files key missing."""
    # given
    session_data = {"performance_status": 1, "performance_rating": 5}

    # when
    result = insert._validate_session_structure(session_data)

    # then
    assert result == {
        "success": False,
        "message": "No raw files provided in session data",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_structure_returns_error_when_raw_files_empty() -> None:
    """Test that _validate_session_structure returns error dict when raw_files list is empty."""
    # given
    session_data = {"performance_status": 1, "raw_files": []}

    # when
    result = insert._validate_session_structure(session_data)

    # then
    assert result == {
        "success": False,
        "message": "No raw files provided in session data",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_structure_returns_error_when_raw_files_not_list() -> None:
    """Test that _validate_session_structure returns error dict when raw_files is not list."""
    # given
    session_data = {"performance_status": 1, "raw_files": {"file_name": "test.d"}}

    # when
    result = insert._validate_session_structure(session_data)

    # then
    assert result == {
        "success": False,
        "message": "raw_files must be a list",
        "error_code": "VALIDATION_ERROR",
    }


# ============================================================================
# Tests for _validate_required_fields
# ============================================================================


def test_validate_required_fields_returns_none_for_complete_fields() -> None:
    """Test that _validate_required_fields returns None when all required fields present."""
    # given
    session_data = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "Good",
    }

    # when
    result = insert._validate_required_fields(session_data)

    # then
    assert result is None


def test_validate_required_fields_returns_error_for_missing_performance_status() -> (
    None
):
    """Test that _validate_required_fields returns error dict when performance_status missing."""
    # given
    session_data = {"performance_rating": 5, "performance_comment": "Good"}

    # when
    result = insert._validate_required_fields(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Missing required fields: performance_status",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_required_fields_returns_error_for_missing_performance_rating() -> (
    None
):
    """Test that _validate_required_fields returns error dict when performance_rating missing."""
    # given
    session_data = {"performance_status": 1, "performance_comment": "Good"}

    # when
    result = insert._validate_required_fields(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Missing required fields: performance_rating",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_required_fields_returns_error_for_missing_performance_comment() -> (
    None
):
    """Test that _validate_required_fields returns error dict when performance_comment missing."""
    # given
    session_data = {"performance_status": 1, "performance_rating": 5}

    # when
    result = insert._validate_required_fields(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Missing required fields: performance_comment",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_required_fields_returns_error_for_multiple_missing_fields() -> None:
    """Test that _validate_required_fields returns error dict listing all missing fields."""
    # given
    session_data = {"performance_status": 1}

    # when
    result = insert._validate_required_fields(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Missing required fields: performance_rating, performance_comment",
        "error_code": "VALIDATION_ERROR",
    }


# ============================================================================
# Tests for _validate_performance_fields
# ============================================================================


def test_validate_performance_fields_returns_none_for_valid_fields() -> None:
    """Test that _validate_performance_fields returns None for valid performance fields."""
    # given
    session_data = {"performance_status": 1, "performance_rating": 3.5}

    # when
    result = insert._validate_performance_fields(session_data)

    # then
    assert result is None


def test_validate_performance_fields_returns_error_for_invalid_status() -> None:
    """Test that _validate_performance_fields returns error dict for invalid status."""
    # given
    session_data = {"performance_status": 2, "performance_rating": 3.5}

    # when
    result = insert._validate_performance_fields(session_data)

    # then
    assert result == {
        "success": False,
        "message": "performance_status must be 0, 1",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_performance_fields_returns_error_for_invalid_rating() -> None:
    """Test that _validate_performance_fields returns error dict for invalid rating."""
    # given
    session_data = {"performance_status": 1, "performance_rating": 6}

    # when
    result = insert._validate_performance_fields(session_data)

    # then
    assert result == {
        "success": False,
        "message": "performance_rating must be an integer or float between 0 and 5",
        "error_code": "VALIDATION_ERROR",
    }


# ============================================================================
# Tests for _validate_performance_status
# ============================================================================


def test_validate_performance_status_returns_error_for_int_2() -> None:
    """Test that _validate_performance_status returns error dict for integer 2."""
    # given
    status = 2

    # when
    result = insert._validate_performance_status(status)

    # then
    assert result == {
        "success": False,
        "message": "performance_status must be 0, 1",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_performance_status_returns_error_for_negative_int() -> None:
    """Test that _validate_performance_status returns error dict for negative integer."""
    # given
    status = -1

    # when
    result = insert._validate_performance_status(status)

    # then
    assert result == {
        "success": False,
        "message": "performance_status must be 0, 1",
        "error_code": "VALIDATION_ERROR",
    }


# ============================================================================
# Tests for _validate_file_fields
# ============================================================================


def test_validate_file_fields_returns_none_for_valid_fields() -> None:
    """Test that _validate_file_fields returns None for all valid field values."""
    # given
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}
    index = 0

    # when
    result = insert._validate_file_fields(file_data, index)

    # then
    assert result is None


def test_validate_file_fields_returns_error_for_empty_file_name() -> None:
    """Test that _validate_file_fields returns error dict for empty string file_name."""
    # given
    file_data = {"file_name": "", "instrument_id": "tims2", "gradient": 44.0}
    index = 0

    # when
    result = insert._validate_file_fields(file_data, index)

    # then
    assert result == {
        "success": False,
        "message": "Raw file at index 0: file_name must be a non-empty string",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_file_fields_returns_error_for_empty_instrument_id() -> None:
    """Test that _validate_file_fields returns error dict for empty string instrument_id."""
    # given
    file_data = {"file_name": "test.d", "instrument_id": "", "gradient": 44.0}
    index = 0

    # when
    result = insert._validate_file_fields(file_data, index)

    # then
    assert result == {
        "success": False,
        "message": "Raw file at index 0: instrument_id must be a non-empty string",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_file_fields_returns_error_for_non_numeric_gradient() -> None:
    """Test that _validate_file_fields returns error dict for non-numeric gradient."""
    # given
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": "text"}
    index = 0

    # when
    result = insert._validate_file_fields(file_data, index)

    # then
    assert result == {
        "success": False,
        "message": "Raw file at index 0: gradient must be a float or int",
        "error_code": "VALIDATION_ERROR",
    }


# ============================================================================
# Tests for _process_raw_file
# ============================================================================


def test_process_raw_file_creates_new_file_when_not_exists(in_memory_db: Path) -> None:
    """Test that _process_raw_file creates new record and returns (id, 'created')."""
    # given
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        conn = connection.get_db_connection()
        cursor = conn.cursor()

        # when
        file_id, action = insert._process_raw_file(cursor, file_data)

        # then
        assert action == "created"
        assert file_id == 1

        # Verify file was actually created
        cursor.execute("SELECT * FROM raw_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        assert row["file_name"] == "test.d"
        assert row["instrument_id"] == "tims2"
        assert row["gradient"] == 44.0  # noqa: PLR2004

        conn.close()


def test_process_raw_file_returns_existing_id_when_exact_match(
    in_memory_db: Path,
) -> None:
    """Test that _process_raw_file returns existing id and 'found_exact_match' when file matches."""
    # given
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        conn = connection.get_db_connection()
        cursor = conn.cursor()

        # Pre-insert the file
        cursor.execute(
            "INSERT INTO raw_files (file_name, instrument_id, gradient) VALUES (?, ?, ?)",
            ("test.d", "tims2", 44.0),
        )
        conn.commit()

        # when
        file_id, action = insert._process_raw_file(cursor, file_data)

        # then
        assert action == "found_exact_match"
        assert file_id == 1

        conn.close()


def test_process_raw_file_updates_when_instrument_differs(in_memory_db: Path) -> None:
    """Test that _process_raw_file updates record and returns (id, 'updated') when instrument_id differs."""
    # given
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        conn = connection.get_db_connection()
        cursor = conn.cursor()

        # Pre-insert file with different instrument
        cursor.execute(
            "INSERT INTO raw_files (file_name, instrument_id, gradient) VALUES (?, ?, ?)",
            ("test.d", "tims1", 44.0),
        )
        conn.commit()

        # when
        file_id, action = insert._process_raw_file(cursor, file_data)

        # then
        assert action == "updated"
        assert file_id == 1

        # Verify update occurred
        cursor.execute("SELECT instrument_id FROM raw_files WHERE id = ?", (file_id,))
        assert cursor.fetchone()["instrument_id"] == "tims2"

        conn.close()


def test_process_raw_file_updates_when_gradient_differs_beyond_tolerance(
    in_memory_db: Path,
) -> None:
    """Test that _process_raw_file updates record and returns (id, 'updated') when gradient differs beyond tolerance."""
    # given - GRADIENT_TOLERANCE = 0.001
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        conn = connection.get_db_connection()
        cursor = conn.cursor()

        # Pre-insert file with gradient that differs by > 0.001
        cursor.execute(
            "INSERT INTO raw_files (file_name, instrument_id, gradient) VALUES (?, ?, ?)",
            ("test.d", "tims2", 44.01),
        )
        conn.commit()

        # when
        file_id, action = insert._process_raw_file(cursor, file_data)

        # then
        assert action == "updated"
        assert file_id == 1

        # Verify gradient was updated
        cursor.execute("SELECT gradient FROM raw_files WHERE id = ?", (file_id,))
        assert cursor.fetchone()["gradient"] == 44.0  # noqa: PLR2004

        conn.close()


def test_process_raw_file_reuses_when_gradient_within_tolerance(
    in_memory_db: Path,
) -> None:
    """Test that _process_raw_file returns 'found_exact_match' when gradient within tolerance."""
    # given - GRADIENT_TOLERANCE = 0.001
    file_data = {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        conn = connection.get_db_connection()
        cursor = conn.cursor()

        # Pre-insert file with gradient that differs by < 0.001
        cursor.execute(
            "INSERT INTO raw_files (file_name, instrument_id, gradient) VALUES (?, ?, ?)",
            ("test.d", "tims2", 44.0005),
        )
        conn.commit()

        # when
        file_id, action = insert._process_raw_file(cursor, file_data)

        # then
        assert action == "found_exact_match"
        assert file_id == 1

        # Verify gradient was NOT updated (still has old value)
        cursor.execute("SELECT gradient FROM raw_files WHERE id = ?", (file_id,))
        assert cursor.fetchone()["gradient"] == 44.0005  # noqa: PLR2004

        conn.close()


# ============================================================================
# Tests for _validate_session_data
# ============================================================================


def test_validate_session_data_returns_none_for_valid_complete_session() -> None:
    """Test that _validate_session_data returns None for fully valid session data."""
    # given
    session_data = {
        "performance_status": 1,
        "performance_rating": 4.5,
        "performance_comment": "Good performance",
        "raw_files": [
            {"file_name": "test1.d", "instrument_id": "tims2", "gradient": 44.0},
            {"file_name": "test2.d", "instrument_id": "tims1", "gradient": 30.0},
        ],
    }

    # when
    result = insert._validate_session_data(session_data)

    # then
    assert result is None


def test_validate_session_data_returns_error_for_invalid_structure() -> None:
    """Test that _validate_session_data returns error dict when structure validation fails."""
    # given
    session_data = None

    # when
    result = insert._validate_session_data(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Invalid session data provided - must be a dictionary",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_data_returns_error_for_missing_required_fields() -> None:
    """Test that _validate_session_data returns error dict when required fields missing."""
    # given
    session_data = {
        "performance_status": 1,
        "raw_files": [
            {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}
        ],
    }

    # when
    result = insert._validate_session_data(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Missing required fields: performance_rating, performance_comment",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_data_returns_error_for_invalid_performance_fields() -> None:
    """Test that _validate_session_data returns error dict when performance fields invalid."""
    # given
    session_data = {
        "performance_status": 1,
        "performance_rating": 6,
        "performance_comment": "Good",
        "raw_files": [
            {"file_name": "test.d", "instrument_id": "tims2", "gradient": 44.0}
        ],
    }

    # when
    result = insert._validate_session_data(session_data)

    # then
    assert result == {
        "success": False,
        "message": "performance_rating must be an integer or float between 0 and 5",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_session_data_returns_error_for_invalid_raw_files() -> None:
    """Test that _validate_session_data returns error dict when raw_files validation fails."""
    # given
    session_data = {
        "performance_status": 1,
        "performance_rating": 4,
        "performance_comment": "Good",
        "raw_files": [{"file_name": "", "instrument_id": "tims2", "gradient": 44.0}],
    }

    # when
    result = insert._validate_session_data(session_data)

    # then
    assert result == {
        "success": False,
        "message": "Raw file at index 0: file_name must be a non-empty string",
        "error_code": "VALIDATION_ERROR",
    }
