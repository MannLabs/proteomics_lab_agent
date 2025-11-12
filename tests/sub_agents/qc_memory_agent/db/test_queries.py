"""Unit tests for qc_memory_agent queries module."""

from __future__ import annotations

import pytest

from proteomics_lab_agent.sub_agents.qc_memory_agent.db import queries
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
