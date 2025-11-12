"""Unit tests for qc_memory_agent queries module."""

from __future__ import annotations

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import queries

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
