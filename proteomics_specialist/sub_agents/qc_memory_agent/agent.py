"""qc_memory agent can store and retrieve past evaluations of proteomics analysis results into a database."""

import logging
from pathlib import Path

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from proteomics_lab_agent.config import config

from . import prompt

logger = logging.getLogger(__name__)

PATH_TO_YOUR_MCP_SERVER_SCRIPT = str((Path(__file__).parent / "server.py").resolve())

MODEL = "gemini-2.5-flash"


def check_model_response(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> None | LlmResponse:
    """Check for LLM errors (like malformed function calls)."""
    logger.info("=== MODEL CALLBACK TRIGGERED ===")
    agent_name = callback_context.agent_name
    logger.info(f"Agent: {agent_name}")

    if llm_response.error_code or llm_response.error_message:
        logger.info(
            f"LLM Error detected: {llm_response.error_code} - {llm_response.error_message}"
        )
        if llm_response.error_code == "MALFORMED_FUNCTION_CALL":
            logger.info("Malformed function call detected - error!")
            error_response = {
                "success": False,
                "message": f"An error occurred: {llm_response.error_message}. Compare the input parameters with the tool specifications and fix them.",
                "error_code": "INPUT_PARAMETER_ERROR",
            }
            callback_context.state["error_response"] = error_response
            callback_context.state["tool_failed"] = True
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"Error occurred: {error_response}")],
                )
            )
    logger.info("No LLM Error detected")
    return None


qc_memory_agent = Agent(
    name="qc_memory_agent",
    model=config.model,
    description="An agent that can store and retrieve past evaluations of proteomics analysis results.",
    instruction=prompt.DB_MCP_PROMPT,
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="python3",
                args=[PATH_TO_YOUR_MCP_SERVER_SCRIPT],
            )
        )
    ],
    after_model_callback=check_model_response,  # Add this
)
