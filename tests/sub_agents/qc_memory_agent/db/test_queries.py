"""Unit tests for qc_memory_agent queries module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import (
    connection,
    insert,
    queries,
)
from proteomics_lab_agent.sub_agents.qc_memory_agent.db.utils import ValidationError

# ============================================================================
# Tests for _validate_query_filters
# ============================================================================


def test_validate_query_filters_returns_none_for_valid_filters() -> None:
    """Test that _validate_query_filters returns None when all filters are valid."""
    # given - all valid filter fields
    filters = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "test",
        "instrument_id": "tims1",
        "gradient": 44.0,
        "file_name": "test.d",
        "created_by_agent_version": "v1.0",
    }

    # when
    result = queries._validate_query_filters(filters)

    # then
    assert result is None


def test_validate_query_filters_returns_error_for_empty_filters() -> None:
    """Test that _validate_query_filters returns error dict when filters dict is empty."""
    # given
    filters = {}

    # when
    result = queries._validate_query_filters(filters)

    # then
    assert result == {
        "success": False,
        "message": "No filter provided",
        "error_code": "VALIDATION_ERROR",
    }


def test_validate_query_filters_returns_error_for_invalid_filter_fields() -> None:
    """Test that _validate_query_filters returns error dict with invalid field names."""
    # given
    filters = {"invalid_field": "value"}

    # when
    result = queries._validate_query_filters(filters)

    # then
    valid_fields = [
        "performance_status",
        "performance_rating",
        "performance_comment",
        "instrument_id",
        "gradient",
        "file_name",
        "created_by_agent_version",
    ]
    assert result == {
        "success": False,
        "message": f"Invalid filter field(s): ['invalid_field']. Valid fields: {valid_fields}",
        "error_code": "VALIDATION_ERROR",
    }


# ============================================================================
# Tests for _build_gradient_condition
# ============================================================================


def test_build_gradient_condition_returns_exact_match_for_float() -> None:
    """Test that _build_gradient_condition returns exact match SQL for float value."""
    # given
    value = 44.0

    # when
    condition, params = queries._build_gradient_condition(value)

    # then
    assert condition == "rf.gradient = ?"
    assert params == [44.0]


def test_build_gradient_condition_returns_range_for_min_max_dict() -> None:
    """Test that _build_gradient_condition returns BETWEEN SQL for min/max dict."""
    # given
    value = {"min": 40.0, "max": 45.0}

    # when
    condition, params = queries._build_gradient_condition(value)

    # then
    assert condition == "rf.gradient BETWEEN ? AND ?"
    assert params == [40.0, 45.0]


def test_build_gradient_condition_returns_gte_for_min_only_dict() -> None:
    """Test that _build_gradient_condition returns >= SQL for min-only dict."""
    # given
    value = {"min": 40.0}

    # when
    condition, params = queries._build_gradient_condition(value)

    # then
    assert condition == "rf.gradient >= ?"
    assert params == [40.0]


def test_build_gradient_condition_returns_lte_for_max_only_dict() -> None:
    """Test that _build_gradient_condition returns <= SQL for max-only dict."""
    # given
    value = {"max": 45.0}

    # when
    condition, params = queries._build_gradient_condition(value)

    # then
    assert condition == "rf.gradient <= ?"
    assert params == [45.0]


def test_build_gradient_condition_returns_tolerance_range_for_tolerance_dict() -> None:
    """Test that _build_gradient_condition returns BETWEEN SQL for tolerance dict."""
    # given
    value = {"value": 44.0, "tolerance": 0.5}

    # when
    condition, params = queries._build_gradient_condition(value)

    # then
    assert condition == "rf.gradient BETWEEN ? AND ?"
    assert params == [43.5, 44.5]


def test_build_gradient_condition_raises_error_for_invalid_dict_format() -> None:
    """Test that _build_gradient_condition raises ValidationError for invalid dict format."""
    # given
    value = {"invalid_key": 44.0}

    # when / then
    with pytest.raises(
        ValidationError,
        match="Invalid gradient filter format. Use 'min'/'max', 'tolerance'/'value', or numeric value.",
    ):
        queries._build_gradient_condition(value)


# ============================================================================
# Tests for _build_filter_conditions
# ============================================================================


def test_build_filter_conditions_returns_conditions_and_params_for_exact_match_filters() -> (
    None
):
    """Test that _build_filter_conditions builds correct SQL for exact match filters."""
    # given
    filters = {"performance_status": 1, "performance_rating": 5}

    # when
    conditions, params = queries._build_filter_conditions(filters)

    # then
    assert conditions == ["pd.performance_status = ?", "pd.performance_rating = ?"]
    assert params == [1, 5]


def test_build_filter_conditions_returns_like_condition_for_performance_comment() -> (
    None
):
    """Test that _build_filter_conditions builds LIKE SQL for performance_comment filter."""
    # given
    filters = {"performance_comment": "Excellent"}

    # when
    conditions, params = queries._build_filter_conditions(filters)

    # then
    assert conditions == ["pd.performance_comment LIKE ?"]
    assert params == ["%Excellent%"]


def test_build_filter_conditions_returns_gradient_condition_for_gradient_filter() -> (
    None
):
    """Test that _build_filter_conditions delegates to _build_gradient_condition for gradient."""
    # given
    filters = {"gradient": {"min": 40.0, "max": 45.0}}

    # when
    conditions, params = queries._build_filter_conditions(filters)

    # then
    assert conditions == ["rf.gradient BETWEEN ? AND ?"]
    assert params == [40.0, 45.0]


def test_build_filter_conditions_handles_multiple_filters() -> None:
    """Test that _build_filter_conditions combines multiple filters correctly."""
    # given
    filters = {
        "performance_status": 1,
        "instrument_id": "tims2",
        "gradient": 44.0,
    }

    # when
    conditions, params = queries._build_filter_conditions(filters)

    # then
    assert conditions == [
        "pd.performance_status = ?",
        "rf.instrument_id = ?",
        "rf.gradient = ?",
    ]
    assert params == [1, "tims2", 44.0]


# ============================================================================
# Tests for query_performance_data (integration tests)
# ============================================================================


def test_query_performance_data_returns_success_with_matching_records(
    in_memory_db: Path,
) -> None:
    """Test that query_performance_data returns success dict with data when records match."""
    # given - populate database with test data
    session_data = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "Excellent performance",
        "raw_files": [
            {"file_name": "test1.d", "instrument_id": "tims2", "gradient": 44.0}
        ],
    }

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        # Insert test data
        insert_result = insert.insert_performance_and_raw_file_info(session_data)
        assert insert_result["success"] is True

        # when - query with matching filter
        filters = {"performance_status": 1}
        result = queries.query_performance_data(filters)

    # then
    assert result == {
        "success": True,
        "message": "Query executed successfully. Found 1 record(s).",
        "data": {
            "results": [
                {
                    "id": 1,
                    "file_name": "test1.d",
                    "instrument_id": "tims2",
                    "gradient": 44.0,
                    "performance_status": 1,
                    "performance_rating": 5.0,
                    "performance_comment": "Excellent performance",
                    "created_by_agent_version": "qc_memory_agent_v1.0",
                }
            ],
            "count": 1,
        },
    }


def test_query_performance_data_returns_empty_results_when_no_matches(
    in_memory_db: Path,
) -> None:
    """Test that query_performance_data returns success dict with empty data when no matches."""
    # given - populate database with test data
    session_data = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "Excellent performance",
        "raw_files": [
            {"file_name": "test1.d", "instrument_id": "tims2", "gradient": 44.0}
        ],
    }

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        # Insert test data
        insert_result = insert.insert_performance_and_raw_file_info(session_data)
        assert insert_result["success"] is True

        # when - query with filter that doesn't match
        filters = {"performance_status": 0}
        result = queries.query_performance_data(filters)

    # then
    assert result == {
        "success": True,
        "message": "Query executed successfully. Found 0 record(s).",
        "data": {"results": [], "count": 0},
    }


def test_query_performance_data_returns_error_for_invalid_filters() -> None:
    """Test that query_performance_data returns error dict for invalid filters."""
    # given
    filters = {"invalid_field": "value"}

    # when
    result = queries.query_performance_data(filters)

    # then
    valid_fields = [
        "performance_status",
        "performance_rating",
        "performance_comment",
        "instrument_id",
        "gradient",
        "file_name",
        "created_by_agent_version",
    ]
    assert result == {
        "success": False,
        "message": f"Invalid filter field(s): ['invalid_field']. Valid fields: {valid_fields}",
        "error_code": "VALIDATION_ERROR",
    }


def test_query_performance_data_combines_multiple_filters(
    in_memory_db: Path,
) -> None:
    """Test that query_performance_data correctly combines multiple filters with AND."""
    # given - populate database with multiple sessions
    session1 = {
        "performance_status": 1,
        "performance_rating": 5,
        "performance_comment": "Excellent",
        "raw_files": [
            {"file_name": "file1.d", "instrument_id": "tims2", "gradient": 44.0}
        ],
    }
    session2 = {
        "performance_status": 1,
        "performance_rating": 3,
        "performance_comment": "Good",
        "raw_files": [
            {"file_name": "file2.d", "instrument_id": "tims1", "gradient": 44.0}
        ],
    }
    session3 = {
        "performance_status": 0,
        "performance_rating": 2,
        "performance_comment": "Poor",
        "raw_files": [
            {"file_name": "file3.d", "instrument_id": "tims2", "gradient": 30.0}
        ],
    }

    with patch.object(connection, "DATABASE_PATH", in_memory_db):
        # Insert test data
        insert.insert_performance_and_raw_file_info(session1)
        insert.insert_performance_and_raw_file_info(session2)
        insert.insert_performance_and_raw_file_info(session3)

        # when - query with multiple filters (should match only session1)
        filters = {
            "performance_status": 1,
            "instrument_id": "tims2",
            "gradient": 44.0,
        }
        result = queries.query_performance_data(filters)

    # then - only file1.d matches all three filters
    assert result == {
        "success": True,
        "message": "Query executed successfully. Found 1 record(s).",
        "data": {
            "results": [
                {
                    "id": 1,
                    "file_name": "file1.d",
                    "instrument_id": "tims2",
                    "gradient": 44.0,
                    "performance_status": 1,
                    "performance_rating": 5.0,
                    "performance_comment": "Excellent",
                    "created_by_agent_version": "qc_memory_agent_v1.0",
                }
            ],
            "count": 1,
        },
    }
