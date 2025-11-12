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
