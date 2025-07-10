"""Python file for testing LLM workflow with evaluations."""

import pathlib
import sys

import dotenv
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables from .env file for testing."""
    dotenv.load_dotenv()


@pytest.mark.asyncio
async def test_with_single_test_file() -> None:
    """Test the agent's basic ability via a session file."""
    await AgentEvaluator.evaluate(
        agent_module="proteomics_specialist",
        eval_dataset_file_path_or_dir="/Users/patriciaskowronek/Documents/proteomics_specialist/proteomics_specialist/question_agent.evalset.json",
        num_runs=1,
    )
