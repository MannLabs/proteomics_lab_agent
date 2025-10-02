"""Python file for testing LLM workflow with custom LLM evaluator."""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import dotenv
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

from . import register_protocol_title_evaluator

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables from .env file for testing & register custom evaluator."""
    dotenv.load_dotenv()
    register_protocol_title_evaluator()


@pytest.mark.asyncio
async def test_eval_agent() -> None:
    """Test the agent evaluator against a evaluation dataset and use logging."""
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    log_dir = Path("./eval_logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"eval_results_{timestamp}.log"

    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            # logging.StreamHandler()  # Console output
        ],
        force=True,  # Override any existing configuration
    )
    logger = logging.getLogger(__name__)
    print(f"Evaluation logs saved to: {log_file}")  # noqa: T201 (Console output for user visibility)

    base_dir = Path(__file__).parent.parent.parent
    eval_file_path = (
        base_dir / "eval/eval_protocol_finding/protocol_finder_converted.evalset.json"
    )

    try:
        await AgentEvaluator.evaluate(
            agent_module="proteomics_lab_agent",
            eval_dataset_file_path_or_dir=str(eval_file_path),
            num_runs=1,
        )
    except (ValueError, TypeError, RuntimeError, ConnectionError):
        logger.exception("Test failed.")
        raise

    finally:
        logging.shutdown()
