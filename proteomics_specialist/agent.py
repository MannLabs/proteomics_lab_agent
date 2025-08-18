"""Root agent is designed to support proteomics researchers."""

import logging

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from proteomics_specialist.config import config

from . import prompt
from .sub_agents.instrument_agent import instrument_agent
from .sub_agents.lab_knowledge_agent import lab_knowledge_agent
from .sub_agents.lab_note_generator_agent import (
    lab_note_benchmark_helper_agent,
    lab_note_generator_agent,
)
from .sub_agents.protocol_generator_agent import protocol_generator_agent
from .sub_agents.qc_memory_agent import qc_memory_agent
from .sub_agents.video_analyzer_agent import video_analyzer_agent

logger = logging.getLogger(__name__)


def get_current_datetime() -> dict:
    """Get current date and time."""
    from datetime import datetime, timezone

    utc_now = datetime.now(timezone.utc)
    local_now = utc_now.astimezone()

    try:
        return {
            "local_time": local_now.isoformat(),
            "utc_time": utc_now.isoformat(),
            "date": local_now.strftime("%Y-%m-%d"),
            "time": local_now.strftime("%H:%M:%S"),
        }
    except Exception as e:
        logging.exception("Error getting datetime.")
        return {"error": str(e)}


root_agent = LlmAgent(
    name="ai_proteomics_adviser",
    model=config.model,
    description="""Agent to support proteomics researchers.""",
    instruction=prompt.PROMPT,
    tools=[
        AgentTool(agent=instrument_agent),
        AgentTool(agent=qc_memory_agent),
        AgentTool(agent=lab_knowledge_agent),
        AgentTool(agent=protocol_generator_agent),
        AgentTool(agent=video_analyzer_agent),
        AgentTool(agent=lab_note_generator_agent),
        AgentTool(agent=lab_note_benchmark_helper_agent),
        FunctionTool(func=get_current_datetime),
    ],
)
