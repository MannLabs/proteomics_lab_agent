"""Root agent is designed to support proteomics researchers."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from proteomics_specialist.config import config

from . import prompt
from .sub_agents.alphakraken_agent import alphakraken_agent
from .sub_agents.database_agent import database_agent
from .sub_agents.protocol_agent import protocol_agent

root_agent = LlmAgent(
    name="ai_proteomics_adviser",
    model=config.model,
    description="""Agent to support proteomics researchers.""",
    instruction=prompt.PROMPT,
    tools=[
        AgentTool(agent=alphakraken_agent),
        AgentTool(agent=database_agent),
        AgentTool(agent=protocol_agent),
    ],
)
