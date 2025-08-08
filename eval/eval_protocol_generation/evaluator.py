"""Evaluator for the lab note generation part."""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from google import genai
from pandas import Series
from pydantic import BaseModel, Field

path_to_append = Path(Path.cwd()).parent.parent
sys.path.append(str(path_to_append))

from .prompt import PROTOCOL_EVALUATION_PROMPT

logger = logging.getLogger(__name__)

EXTRACTION_MODEL = "gemini-2.5-flash"
OUTPUT_DIR_DEFAULT = "./protocol_eval_logs"
PROTOCOL_DISPLAY_MAX_LENGTH = 100

DEFAULT_RATING_COLUMNS = {
    "completeness": "completeness_rating",
    "accuracy": "technical_accuracy_rating",
    "logic": "logical_flow_rating",
    "safety": "safety_rating",
    "formatting": "formatting_rating",
}

from eval.eval_lab_note_generation.evaluator import (
    setup_logging,
)


class ProtocolRatingPerSection(BaseModel):
    """Represents the evaluation of a single protocol section."""

    section: str = Field(
        description="Name of the protocol section (e.g., 'Title', 'Abstract', 'Procedure - Step 1')"
    )
    ground_truth_text: str = Field(
        description="Text content from the ground truth protocol"
    )
    ai_generated_text: str = Field(
        description="Text content from the AI-generated protocol"
    )

    completeness_rating: int = Field(
        ge=1, le=5, description="Completeness rating from 1-5"
    )
    completeness_explanation: str = Field(
        description="Explanation for completeness rating"
    )

    technical_accuracy_rating: int = Field(
        ge=1, le=5, description="Technical accuracy rating from 1-5"
    )
    technical_accuracy_explanation: str = Field(
        description="Explanation for technical accuracy rating"
    )

    logical_flow_rating: int = Field(
        ge=1, le=5, description="Logical flow rating from 1-5"
    )
    logical_flow_explanation: str = Field(
        description="Explanation for logical flow rating"
    )

    safety_rating: int = Field(ge=1, le=5, description="Safety rating from 1-5")
    safety_explanation: str = Field(description="Explanation for safety rating")

    formatting_rating: int = Field(ge=1, le=5, description="Formatting rating from 1-5")
    formatting_explanation: str = Field(description="Explanation for formatting rating")

    notes: str = Field(default="", description="Additional observations or comments")


class ProtocolRating(BaseModel):
    """Represents the complete rating of all sections."""

    sections: list[ProtocolRatingPerSection] = Field(
        ...,
        description="A list of ratings, where each item corresponds to a protocol section.",
    )


def calculate_protocol_ratings(
    df_eval: pd.DataFrame,
    column_config: dict | None = None,
) -> dict:
    """Calculate average ratings across evaluation criteria from a dataframe of protocol evaluations.

    Parameters
    ----------
    df_eval : pd.DataFrame
        DataFrame containing evaluation ratings for protocols
    column_config : dict, optional
        Dictionary mapping criterion names to column names. If None, uses DEFAULT_RATING_COLUMNS.
        Expected keys: 'completeness', 'accuracy', 'logic', 'safety', 'formatting'

    Returns
    -------
    dict
        Dictionary containing average ratings for each criterion and an overall rating

    """
    config = column_config or DEFAULT_RATING_COLUMNS

    mean_completeness = df_eval[config["completeness"]].mean()
    mean_accuracy = df_eval[config["accuracy"]].mean()
    mean_logic = df_eval[config["logic"]].mean()
    mean_safety = df_eval[config["safety"]].mean()
    mean_formatting = df_eval[config["formatting"]].mean()

    result_dict = {
        "Completeness": mean_completeness,
        "Technical Accuracy": mean_accuracy,
        "Logical Flow": mean_logic,
        "Safety": mean_safety,
        "Formatting": mean_formatting,
        "Overall": np.mean(
            [mean_completeness, mean_accuracy, mean_logic, mean_safety, mean_formatting]
        ),
    }

    return {k: float(v) for k, v in result_dict.items()}


def generate_protocols_evaluation(
    protocol_gt: str,
    protocol_ai: str,
) -> tuple[str, Any]:
    """Generate an evaluation of AI-generated protocols against ground truth protocols.

    Parameters
    ----------
    protocol_gt : List[str]
        The ground truth protocols (benchmark) represented as a list of strings
    protocol_ai : List[str]
        The AI-generated protocols to evaluate represented as a list of strings

    Returns
    -------
    tuple[str, Any]
        A tuple containing (evaluation_text, usage_metadata)

    """
    custom_prompt = PROTOCOL_EVALUATION_PROMPT.format(
        gt_protocol=protocol_gt, generated_protocol=protocol_ai
    )

    client = genai.Client()
    response = client.models.generate_content(
        model=EXTRACTION_MODEL,
        contents=custom_prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": ProtocolRating,
        },
    )

    return response.parsed, response.usage_metadata


def _run_single_evaluation(
    row: Series,
    eval_set_name: str,
    run_number: int,
    selected_function: dict[str, Callable],
) -> dict | None:
    """Execute a single protocol generation and evaluation for a benchmark row.

    This function performs a complete evaluation for one row of the benchmark data. It
    generates protocols, evaluates these protocols, processes the evaluation,
    and returns a summary.

    Parameters
    ----------
    row: pandas.Series
        A single row from the benchmark DataFrame, containing details like user prompt,
        'ground truth protocol'.
    eval_set_name: str
        The name of the evaluation set the current row belongs to.
    run_number: int
        The current run number for this evaluation set.
    selected_function: dict[str, Callable]
        Protocol generation name and function that takes inputs and returns
        (generated_protocol, usage_metadata)

    Returns
    -------
    dict | None
        A dictionary containing the evaluation results for the single run if successful,
        otherwise returns None if an error occurs.

    """
    logger.info(f"\n{'-' * 40}")
    logger.info(f"Run {run_number} for eval set: {eval_set_name}")
    logger.info(f"{'-' * 40}")

    try:
        logger.info("Step 3: Generating protocol ...")

        start_time = time.time()
        generated_protocol = selected_function["function"](row["user_prompt"])
        end_time = time.time()
        protocol_generation_time = end_time - start_time

        logger.info("Step 4: Evaluating protocol against ground truth protocol ...")
        rating_response, usage_metadata = generate_protocols_evaluation(
            row["ground_truth_protocol"],
            generated_protocol["protocol"],
        )

        df_rating = pd.DataFrame(
            [section.model_dump() for section in rating_response.sections]
        )
        dict_rating = calculate_protocol_ratings(df_rating)

        result = {
            "eval_set": eval_set_name,
            "eval_set_index": row.name + 1,
            "run": run_number,
            "function_name": selected_function["name"],
            "protocol": generated_protocol["protocol"],
            "protocol_generation_time_seconds": protocol_generation_time,
            "usage_metadata_protocol_generation": generated_protocol["usage_metadata"],
            "summary_rating": dict_rating,
            "complete_rating": df_rating.to_dict("records"),
        }
        logger.info(
            f"Run {run_number} for eval set {eval_set_name} completed successfully"
        )
    except FileNotFoundError:
        logger.exception(
            f"Required file not found for eval set {eval_set_name}, run {run_number}."
        )
    except (ValueError, SyntaxError):
        logger.exception(
            f"Data parsing error for eval set {eval_set_name}, run {run_number}."
        )
        logger.exception(f"Raw error_dict content: {row.get('error_dict')}")
    except Exception:
        logger.exception(
            f"An unexpected error occurred for eval set {eval_set_name}, run {run_number}."
        )
    else:
        return result
    return None


def _load_benchmark_data(csv_file: str) -> pd.DataFrame:
    """Load and validate benchmark data from CSV file.

    Parameters
    ----------
    csv_file : str
        Path to the CSV file containing benchmark data

    Returns
    -------
    pd.DataFrame
        Loaded benchmark data

    Raises
    ------
    FileNotFoundError
        If the specified CSV file does not exist
    pd.errors.ParserError
        If the CSV file is corrupted or cannot be parsed

    """
    try:
        logger.info("Step 1: Loading benchmark data...")
        return pd.read_csv(csv_file)
    except FileNotFoundError:
        logger.exception(
            f"Failed to load CSV file: The file '{csv_file}' was not found."
        )
        raise
    except pd.errors.ParserError:
        logger.exception("Failed to parse CSV file.")
        raise


def _setup_output_directory(output_dir: str) -> None:
    """Create output directory if it doesn't exist.

    Parameters
    ----------
    output_dir : str
        Directory path to create

    Raises
    ------
    OSError
        If the output directory cannot be created

    """
    try:
        logger.info("Step 2: Creating output directory...")
        Path(output_dir).mkdir(exist_ok=True)
    except OSError:
        logger.exception("Failed to create output directory.")
        raise


def _process_eval_set(
    row: pd.Series,
    function_list: list[dict[str, Callable]],
    num_runs: int,
) -> list[dict]:
    """Process a single evaluation set with all function configurations.

    Parameters
    ----------
    row : pd.Series
        Row from benchmark data containing eval set information
    function_list : list[dict[str, Callable]]
        List of protocol generation functions to evaluate
    num_runs : int
        Number of runs per function configuration

    Returns
    -------
    list[dict]
        Results from all runs for this evaluation set

    """
    eval_set_name = row["eval_set_name"]

    eval_set_results = []

    for selected_function in function_list:
        logger.info(
            f"Testing configuration: {selected_function['name']} for {num_runs!s} times"
        )

        for run in range(1, num_runs + 1):
            result = _run_single_evaluation(row, eval_set_name, run, selected_function)
            if result:
                eval_set_results.append(result)

    logger.info(
        f"\nEval set {eval_set_name} completed - {len(eval_set_results)} runs processed successfully"
    )

    return eval_set_results


def _save_eval_set_results(
    eval_set_name: str, eval_set_results: list[dict], output_dir: str
) -> None:
    """Save results for a single evaluation set.

    Parameters
    ----------
    eval_set_name : str
        Name of the evaluation set
    eval_set_results : list[dict]
        Results to save
    output_dir : str
        Output directory path

    """
    if not eval_set_results:
        return

    try:
        eval_set_output_file = (
            Path(output_dir) / f"eval_set_{eval_set_name}_all_runs.json"
        )
        with Path.open(eval_set_output_file, "w") as f:
            json.dump(eval_set_results, f, indent=2, default=str)
        logger.info(f"Eval set {eval_set_name} results saved to {eval_set_output_file}")
    except Exception:
        logger.exception(f"Failed to save eval set {eval_set_name} results.")


def _save_final_results(all_results: list[dict], output_dir: str) -> None:
    """Save final combined results.

    Parameters
    ----------
    all_results : list[dict]
        All evaluation results
    output_dir : str
        Output directory path

    """
    try:
        final_output_file = Path(output_dir) / "all_eval_sets_all_runs.json"
        with Path.open(final_output_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        logger.info(f"Final results saved to {final_output_file}")
    except Exception:
        logger.exception("Failed to save final results.")


async def evaluate_protocols(
    csv_file: str,
    function_list: list[dict[str, Callable]],
    num_runs: int = 1,
    output_dir: str = OUTPUT_DIR_DEFAULT,
) -> list[dict]:
    """Execute a lab note evaluation.

    This function orchestrates the entire evaluation process. It loads benchmark data from a CSV file,
    iterates through each evaluation set, and performs a specified number of runs for each set.
    The function generates protocols, evaluates them, and saves the
    results in JSON files for each evaluation set and a combined file for all runs.

    Parameters
    ----------
    csv_file : str
        The path to the CSV file containing the benchmark data.
    function_list : List[dict[str, Callable]]
        List of protocol generation names and functions to evaluate
    num_runs : int, optional
        The number of times to run the evaluation for each benchmark entry. Defaults to 1.
    output_dir : str, optional
        The directory where the evaluation logs and results will be saved.
        Defaults to OUTPUT_DIR_DEFAULT.

    Returns
    -------
    List[Dict]
        A list of dictionaries, where each dictionary contains the complete evaluation
        results for a single run.

    Raises
    ------
    FileNotFoundError
        If the specified CSV file does not exist.
    pd.errors.ParserError
        If the CSV file is corrupted or cannot be parsed.
    OSError
        If the output directory cannot be created.

    """
    setup_logging()
    logger.info("=== STARTING EVALUATION ===")
    logger.info(f"CSV file: {csv_file}")
    logger.info(f"Number of runs: {num_runs}")

    df_benchmark_data = _load_benchmark_data(csv_file)
    _setup_output_directory(output_dir)

    all_results = []
    total_eval_sets = len(df_benchmark_data)

    for index, row in df_benchmark_data.iterrows():
        logger.info(f"\n{'=' * 60}")
        logger.info(
            f"PROCESSING EVAL SET: {row['eval_set_name']} ({index + 1}/{total_eval_sets})"
        )
        eval_set_results = _process_eval_set(row, function_list, num_runs)
        all_results.extend(eval_set_results)
        _save_eval_set_results(row["eval_set_name"], eval_set_results, output_dir)

    _save_final_results(all_results, output_dir)

    logger.info("EVALUATION COMPLETE")
    logger.info(f"Total cases processed: {len(all_results)}")
    logger.info(f"Results saved to: {output_dir}")

    return all_results
