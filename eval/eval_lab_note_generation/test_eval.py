"""Test file for lab note error analysis."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from .eval_analysis_run import EvaluationAnalyzer
from .evaluator import evaluate_lab_notes

logger = logging.getLogger(__name__)

TEST_THRESHOLD = 0.5


def setup_logging() -> Path:
    """Setup logging for lab note evaluation."""
    log_dir = Path("./eval_logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"eval_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        force=True,
    )

    return log_file, timestamp


@pytest.mark.asyncio
async def test_lab_note_standalone_evaluation() -> None:
    """Test lab note evaluation using standalone approach (backward compatibility)."""
    log_file, timestamp = setup_logging()
    logger.info(f"Starting standalone lab note evaluation. Logs: {log_file}")

    try:
        # output_dir = "./eval_lab_note_results/result_20250815_112915"
        output_dir = f"./eval_lab_note_results/result_{timestamp}"
        results = await evaluate_lab_notes(
            csv_file="benchmark_data.csv", num_runs=1, output_dir=output_dir
        )

        logger.info(
            f"Standalone evaluation completed. Processed {len(results)} total cases"
        )

        analyzer = EvaluationAnalyzer(output_dir=output_dir)
        metrics_dict = analyzer.run_complete_analysis(
            Path(output_dir) / "all_eval_sets_all_runs.json"
        )

        accuracy = metrics_dict["Accuracy"]
        precision = metrics_dict["Precision (Positive Predictive Value)"]
        recall = metrics_dict["Recall (Sensitivity, True Positive Rate)"]
        f1_score = metrics_dict["F1 Score"]

        logger.info(f"Accuracy: {accuracy}")
        logger.info(f"Precision: {precision}")
        logger.info(f"Recall: {recall}")
        logger.info(f"F1 Score: {f1_score}")

        assert accuracy >= TEST_THRESHOLD, (
            f"Accuracy {accuracy:.3f} is below minimum threshold of {TEST_THRESHOLD}"
        )
        assert precision >= TEST_THRESHOLD, (
            f"Precision {precision:.3f} is below minimum threshold of {TEST_THRESHOLD}"
        )
        assert recall >= TEST_THRESHOLD, (
            f"Recall {recall:.3f} is below minimum threshold of {TEST_THRESHOLD}"
        )
        assert f1_score >= TEST_THRESHOLD, (
            f"F1 Score {f1_score:.3f} is below minimum threshold of {TEST_THRESHOLD}"
        )

        logger.info("All metrics meet the minimum threshold of {TEST_THRESHOLD}")

    except Exception:
        logger.exception("Standalone evaluation failed.")
        raise
    finally:
        logging.shutdown()
