"""Unit tests for instrument_agent.agent module."""

from __future__ import annotations

from unittest.mock import patch

# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


@patch.dict("os.environ", {"ALPHAKRAKEN_MCP_URL": "http://localhost:8080/mcp"})
def test_instrument_agent_instantiation() -> None:
    """Test that instrument_agent is instantiated correctly with all expected attributes."""
    # given/when
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

    from proteomics_lab_agent.config import config
    from proteomics_lab_agent.sub_agents.instrument_agent import agent

    # then
    assert agent.instrument_agent.name == "instrument_agent"
    assert (
        agent.instrument_agent.description
        == "An agent that can retrieve proteomics analysis results."
    )
    assert agent.instrument_agent.model == config.model
    assert agent.instrument_agent.instruction == agent.prompt.KRAKEN_MCP_PROMPT
    assert (
        "You are an expert in interacting with a database"
        in agent.instrument_agent.instruction
    )
    assert len(agent.instrument_agent.tools) == 1
    assert isinstance(agent.instrument_agent.tools[0], MCPToolset)
