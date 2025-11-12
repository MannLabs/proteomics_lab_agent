"""Unit tests for qc_memory_agent insert module."""

from __future__ import annotations

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import insert

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
