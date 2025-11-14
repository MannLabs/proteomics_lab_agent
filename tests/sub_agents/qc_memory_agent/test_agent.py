"""Unit tests for qc_memory_agent.agent module."""

from __future__ import annotations

from unittest.mock import MagicMock

from google.genai import types

from proteomics_lab_agent.sub_agents.qc_memory_agent import agent

# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


def test_check_model_response_returns_none_when_no_error() -> None:
    """Test that check_model_response returns None when there's no error in LlmResponse."""
    # given
    mock_callback_context = MagicMock()
    mock_callback_context.agent_name = "test_agent"
    mock_callback_context.state = {}

    mock_llm_response = MagicMock()
    mock_llm_response.error_code = None
    mock_llm_response.error_message = None

    # when
    result = agent.check_model_response(mock_callback_context, mock_llm_response)

    # then
    assert result is None


# ============================================================================
# ERROR CASE TESTS
# ============================================================================


def test_check_model_response_returns_error_response_for_malformed_function_call() -> (
    None
):
    """Test that check_model_response returns error response when MALFORMED_FUNCTION_CALL error is detected."""
    # given
    mock_callback_context = MagicMock()
    mock_callback_context.agent_name = "test_agent"
    mock_callback_context.state = {}

    mock_llm_response = MagicMock()
    mock_llm_response.error_code = "MALFORMED_FUNCTION_CALL"
    mock_llm_response.error_message = "Invalid function parameter format"

    # when
    result = agent.check_model_response(mock_callback_context, mock_llm_response)

    # then
    assert result is not None
    assert isinstance(result.content, types.Content)
    assert result.content.role == "model"
    assert len(result.content.parts) == 1
    assert "Error occurred:" in result.content.parts[0].text

    assert mock_callback_context.state["tool_failed"] is True
    assert mock_callback_context.state["error_response"] == {
        "success": False,
        "message": "An error occurred: Invalid function parameter format. Compare the input parameters with the tool specifications and fix them.",
        "error_code": "INPUT_PARAMETER_ERROR",
    }


def test_check_model_response_returns_none_for_non_malformed_error_code() -> None:
    """Test that check_model_response returns None when error_code is present but not MALFORMED_FUNCTION_CALL."""
    # given
    mock_callback_context = MagicMock()
    mock_callback_context.agent_name = "test_agent"
    mock_callback_context.state = {}

    mock_llm_response = MagicMock()
    mock_llm_response.error_code = "OTHER_ERROR"
    mock_llm_response.error_message = "Some other error"

    # when
    result = agent.check_model_response(mock_callback_context, mock_llm_response)

    # then
    assert result is None
    assert "error_response" not in mock_callback_context.state
    assert "tool_failed" not in mock_callback_context.state


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_check_model_response_handles_error_message_without_error_code() -> None:
    """Test that check_model_response returns None when only error_message is present without error_code."""
    # given
    mock_callback_context = MagicMock()
    mock_callback_context.agent_name = "test_agent"
    mock_callback_context.state = {}

    mock_llm_response = MagicMock()
    mock_llm_response.error_code = None
    mock_llm_response.error_message = "Some error message"

    # when
    result = agent.check_model_response(mock_callback_context, mock_llm_response)

    # then
    assert result is None
    assert "error_response" not in mock_callback_context.state
    assert "tool_failed" not in mock_callback_context.state


def test_check_model_response_handles_empty_error_message() -> None:
    """Test that check_model_response handles MALFORMED_FUNCTION_CALL with empty error message."""
    # given
    mock_callback_context = MagicMock()
    mock_callback_context.agent_name = "test_agent"
    mock_callback_context.state = {}

    mock_llm_response = MagicMock()
    mock_llm_response.error_code = "MALFORMED_FUNCTION_CALL"
    mock_llm_response.error_message = ""

    # when
    result = agent.check_model_response(mock_callback_context, mock_llm_response)

    # then
    assert result is not None
    assert mock_callback_context.state["error_response"] == {
        "success": False,
        "message": "An error occurred: . Compare the input parameters with the tool specifications and fix them.",
        "error_code": "INPUT_PARAMETER_ERROR",
    }


def test_check_model_response_preserves_existing_state() -> None:
    """Test that check_model_response preserves existing state when adding error information."""
    # given
    mock_callback_context = MagicMock()
    mock_callback_context.agent_name = "test_agent"
    mock_callback_context.state = {"existing_key": "existing_value"}

    mock_llm_response = MagicMock()
    mock_llm_response.error_code = "MALFORMED_FUNCTION_CALL"
    mock_llm_response.error_message = "Invalid parameters"

    # when
    result = agent.check_model_response(mock_callback_context, mock_llm_response)

    # then
    assert result is not None
    assert mock_callback_context.state["existing_key"] == "existing_value"
    assert mock_callback_context.state["tool_failed"] is True
    assert "error_response" in mock_callback_context.state


# ============================================================================
# AGENT INSTANTIATION TESTS
# ============================================================================


def test_qc_memory_agent_instantiation() -> None:
    """Test that qc_memory_agent is instantiated correctly with all expected attributes."""
    # given/when
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

    from proteomics_lab_agent.config import config

    # then
    assert agent.qc_memory_agent.name == "qc_memory_agent"
    assert (
        agent.qc_memory_agent.description
        == "An agent that can store and retrieve past evaluations of proteomics analysis results."
    )
    assert agent.qc_memory_agent.model == config.model
    assert agent.qc_memory_agent.instruction == agent.prompt.DB_MCP_PROMPT
    assert (
        "You are a highly proactive and efficient assistant"
        in agent.qc_memory_agent.instruction
    )
    assert len(agent.qc_memory_agent.tools) == 1
    assert isinstance(agent.qc_memory_agent.tools[0], MCPToolset)
    assert agent.qc_memory_agent.after_model_callback == agent.check_model_response
