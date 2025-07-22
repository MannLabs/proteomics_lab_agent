"""Python file for testing LLM workflow with evaluations."""

import logging
import sys
from pathlib import Path

import dotenv
import pytest
from google.adk.cli.utils import logs
from google.adk.evaluation.agent_evaluator import AgentEvaluator

logger = logging.getLogger(__name__)

# import warnings

# # Ignors following bug: common asyncio/anyio cleanup issue where async context managers (specifically MCP stdio clients) are being torn down across different asyncio tasks.
# class IgnoreCancelScopeFilter(logging.Filter):
#     def filter(self, record):
#         message = record.getMessage() if hasattr(record, 'getMessage') else str(record.msg)
#         return not any(phrase in message for phrase in [
#             "Attempted to exit cancel scope",
#             "unhandled errors in a TaskGroup",
#             "stdio_client",
#             "async_generator object",
#             "GeneratorExit"
#         ])

# for logger_name in ['asyncio', 'anyio', 'mcp', 'root']:
#     logger = logging.getLogger(logger_name)
#     logger.addFilter(IgnoreCancelScopeFilter())

# logging.getLogger().addFilter(IgnoreCancelScopeFilter())


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables from .env file for testing."""
    dotenv.load_dotenv()


@pytest.mark.asyncio
async def test_eval_agent() -> None:
    # async def test_eval_agent(caplog) -> None:
    """Test the agent evaluator with a specific evaluation dataset."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # log_file_path = logs.log_to_tmp_folder(
    logs.log_to_tmp_folder(
        level=logging.INFO,
        sub_folder="proteomics_test_logs",
        log_file_prefix="eval_results",
    )

    try:
        await AgentEvaluator.evaluate(
            agent_module="proteomics_specialist",
            eval_dataset_file_path_or_dir=(
                "/Users/patriciaskowronek/Documents/proteomics_specialist/proteomics_specialist/video_analyzer_agent_2.evalset.json"
            ),
            num_runs=1,
        )
    except (ValueError, TypeError, RuntimeError, ConnectionError):
        logger.exception("Test failed.")
        raise
