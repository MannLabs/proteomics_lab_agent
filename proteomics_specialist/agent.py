from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.alphakraken import alphakraken_agent
from .sub_agents.database import database_agent

# MODEL = "gemini-2.5-pro-preview-03-25"
MODEL = "gemini-2.5-flash"

adviser_coordinator = LlmAgent(
   name="ai_proteomics_adviser",
   model=MODEL,
   description="""Agent to support proteomics researchers.
   """,
   instruction=prompt.PROMPT,
   tools=[AgentTool(agent=alphakraken_agent), AgentTool(agent=database_agent)]
)

root_agent = adviser_coordinator
