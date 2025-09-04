"""Evaluator for the lab note generation part."""

import ast
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import pandas as pd
from google import genai
from pandas import Series
from pydantic import BaseModel

path_to_append = Path(Path.cwd()).parent.parent
sys.path.append(str(path_to_append))

from proteomics_specialist.sub_agents.lab_note_generator_agent import agent
from proteomics_specialist.sub_agents.lab_note_generator_agent.prompt import (
    CLASS_ERROR_CATEGORIES_PROMPT,
)

from .eval_analysis_data import ERROR_TYPES_IDS, SKILL_TYPES
from .prompt import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

EXTRACTION_MODEL = "gemini-2.5-flash"
OUTPUT_DIR_DEFAULT = "./lab_note_eval_logs"
PROTOCOL_DISPLAY_MAX_LENGTH = 100
T = TypeVar("T")


@dataclass
class StepResult(BaseModel):
    """Represents the AI's analysis of a single protocol step."""

    step: float
    ai_response: str
    ai_class: str


@dataclass
class ErrorExtraction(BaseModel):
    """Represents the complete AI error extraction response."""

    steps: list[StepResult]


def setup_logging() -> None:
    """Sets up basic logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def extract_errors(
    lab_notes: list[str],
    docu_steps: list[str],
) -> tuple[str, dict[str, Any]]:
    """Extract the identified errors of AI-generated lab notes using a LLM request.

    Parameters
    ----------
    lab_notes : list
        The AI-generated lab notes to extract represented as a list of strings
    docu_steps : list[str]
        The steps in the protocol to compare against the lab notes

    Returns
    -------
    tuple
        A tuple containing (evaluation_text, usage_metadata)

    """
    custom_prompt = EXTRACTION_PROMPT.format(
        docu_steps=docu_steps,
        lab_notes=lab_notes,
        CLASS_ERROR_CATEGORIES_PROMPT=CLASS_ERROR_CATEGORIES_PROMPT,
    )

    client = genai.Client()
    response = client.models.generate_content(
        model=EXTRACTION_MODEL,
        contents=custom_prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": ErrorExtraction,
        },
    )

    return response.parsed, response.usage_metadata


def identify_error_type(row: Series) -> str:
    """Identify the type of error based on benchmark and AI response.

    Parameters
    ----------
    row : Any
        A row from a DataFrame containing Benchmark, AI Response, Class, and AI Class columns

    Returns
    -------
    str
        The identified error type classification

    """
    benchmark = row["Benchmark"]
    ai_response = row["AI Response"]
    ai_class = row["AI Class"]
    benchmark_class = row["Class"]

    result = "Unknown"

    if pd.isna(benchmark):
        if ai_class == "Addition":
            result = "Addition by model"
        elif benchmark_class == "Addition" and ai_class == "N/A":
            result = "False Negative"
    elif benchmark == "No Error":
        if ai_response == "No Error":
            result = "No Error (Correctly Identified)"
        elif ai_response == "Error":
            result = "False Positive"
    elif benchmark == "Error":
        if ai_response == "Error":
            result = "Error (Correctly Identified)"
        elif ai_response == "No Error":
            result = "False Negative"

    return result


def classify_error_type(row: Series) -> str:
    """Classify the error type as correct, incorrect, or N/A based on identification and class.

    Parameters
    ----------
    row : Any
        A row from a DataFrame containing Identification, Class, and AI Class columns

    Returns
    -------
    str
        Classification of the error type as 'correct', 'incorrect', or 'N/A'

    """
    if row["Identification"] == "Error (Correctly Identified)":
        if row["Class"] == row["AI Class"]:
            return "correct"
        return "incorrect"
    return "N/A"


def get_counts(df: pd.DataFrame, prefix: str) -> dict[str, int]:
    """Count occurrences of different classes and skills.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame containing the error analysis results. It is expected to have
        at least the columns 'Class' and 'Skill'.
    prefix : str
        A string prefix to be added to the name of each count in the output
        dictionary, such as 'Type' or 'All Type'.

    Returns
    -------
    dict[str, int]
        A dictionary where the keys are the prefixed count names (e.g., 'Type Omitted',
        'All Type SpatialOrientation') and the values are their corresponding integer
        counts.

    """
    class_counts = df["Class"].value_counts().to_dict()
    counts = {f"{prefix} {cls}": class_counts.get(cls, 0) for cls in ERROR_TYPES_IDS}

    for class_val in ERROR_TYPES_IDS:
        for skill_val in SKILL_TYPES:
            count = len(df[(df["Class"] == class_val) & (df["Skill"] == skill_val)])
            counts[f"{prefix} {class_val} {skill_val}"] = count

    return counts


def generate_error_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Generate a summary dictionary of error identification and classification statistics.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing error analysis results with 'Benchmark', 'Identification',
        and 'Classification' columns

    Returns
    -------
    Dict[str, Any]
        A nested dictionary containing error identification and classification statistics

    """
    total_evaluated_steps = len(df)
    addition_by_model = len(df[df["Identification"] == "Addition by model"])
    steps_evaluated_minus_added_by_ai = total_evaluated_steps - addition_by_model

    tp = len(df[df["Identification"] == "Error (Correctly Identified)"])
    tn = len(df[df["Identification"] == "No Error (Correctly Identified)"])
    fp = len(df[df["Identification"] == "False Positive"])
    fn = len(df[df["Identification"] == "False Negative"])

    total_errors_analyzed = tp + fn
    correctly_classified_errors = len(df[df["Classification"] == "correct"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    balanced_accuracy = (recall + specificity) / 2
    classification_accuracy = correctly_classified_errors / tp if tp > 0 else 0

    summary_dict = {
        "True Positives (TP) = Correct error identifications": tp,
        "True Negatives (TN) = Correct no error identifications": tn,
        "False Positives (fp)": fp,
        "False Negatives (fn)": fn,
        "Total steps evaluated": total_evaluated_steps,
        "Steps evaluated minus added by AI": steps_evaluated_minus_added_by_ai,
        "Addition by model": addition_by_model,
        "Errors evaluated": total_errors_analyzed,
        "Classification Accuracy": classification_accuracy,
        "Accuracy": accuracy,
        "Precision (Positive Predictive Value)": precision,
        "Recall (Sensitivity, True Positive Rate)": recall,
        "Specificity (True Negative Rate)": specificity,
        "F1 Score": f1_score,
        "Balanced Accuracy": balanced_accuracy,
        "False Positive Rate": fp / (fp + tn) if (fp + tn) > 0 else 0,
        "False Negative Rate": fn / (tp + fn) if (tp + fn) > 0 else 0,
        "False Discovery Rate": fp / (tp + fp) if (tp + fp) > 0 else 0,
        "False Omission Rate": fn / (tn + fn) if (tn + fn) > 0 else 0,
        "Positive Predictive Value": precision,
        "Negative Predictive Value": tn / (tn + fn) if (tn + fn) > 0 else 0,
        "Total errors analyzed": total_errors_analyzed,
        "Correctly classified errors": correctly_classified_errors,
    }

    error_correctly_identified = df[
        df["Identification"] == "Error (Correctly Identified)"
    ]
    summary_dict.update(get_counts(error_correctly_identified, "Type"))
    possible_error = df[df["Identification"] != "Addition by model"]
    summary_dict.update(get_counts(possible_error, "All Type"))

    return summary_dict


def remove_zeros(d: T) -> T:
    """Recursively removes keys with a value of 0 from a dictionary."""
    if not isinstance(d, dict):
        return d

    result = {}
    for k, v in d.items():
        if v == 0:
            continue

        cleaned_v = remove_zeros(v)
        if cleaned_v != {}:
            result[k] = cleaned_v
    return result


def _process_errors_dataframes(row: Series, error_response: Any) -> pd.DataFrame:  # noqa: ANN401
    """Helper function to merge benchmark and AI error data into a DataFrame."""
    # Parsing error dictionary
    error_dict = ast.literal_eval(row["error_dict"])

    df_error_ai = pd.DataFrame([step.model_dump() for step in error_response.steps])
    df_error_ai.columns = ["Step", "AI Response", "AI Class"]

    df_error_benchmark = pd.DataFrame(error_dict)
    df_errors = df_error_benchmark.merge(df_error_ai, on="Step", how="outer")

    df_errors["Identification"] = df_errors.apply(identify_error_type, axis=1)
    df_errors["Classification"] = df_errors.apply(classify_error_type, axis=1)

    return df_errors


def _run_single_evaluation(
    row: Series, eval_set_name: str, run_number: int
) -> dict | None:
    """Execute a single evaluation run for a benchmark row.

    This function performs a complete evaluation for one row of the benchmark data. It
    generates lab notes, extracts errors using an AI model, processes the results,
    and returns a summary of the findings.

    Parameters
    ----------
    row : pandas.Series
        A single row from the benchmark DataFrame, containing details like 'video_path',
        'protocol', and 'error_dict'.
    eval_set_name : str
        The name of the evaluation set the current row belongs to.
    run_number : int
        The current run number for this evaluation set.

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
        logger.info("Step 3: Generating lab notes ...")
        protocol_display = (
            f"Protocol: {row['protocol'][:PROTOCOL_DISPLAY_MAX_LENGTH]}..."
            if len(str(row["protocol"])) > PROTOCOL_DISPLAY_MAX_LENGTH
            else f"Protocol: {row['protocol']}"
        )
        logger.info(f"Video path: {row['video_path']}")
        logger.info(protocol_display)

        start_time = time.time()
        generated_lab_note = agent.generate_lab_notes(
            row["video_path"],
            None,
            row["protocol"],
        )
        end_time = time.time()
        lab_note_generation_time = end_time - start_time

        # Parsing error dictionary
        error_dict = ast.literal_eval(row["error_dict"])
        steps_list = [item["Step"] for item in error_dict]

        logger.info("Step 4: Extracting errors with AI ...")
        error_response, usage_metadata = extract_errors(
            generated_lab_note["lab_notes"], steps_list
        )

        df_errors = _process_errors_dataframes(row, error_response)

        summary_dict = generate_error_summary(df_errors)
        filtered_dict = remove_zeros(summary_dict)

        result = {
            "eval_set": eval_set_name,
            "eval_set_index": row.name + 1,
            "run": run_number,
            "lab_notes": generated_lab_note["lab_notes"],
            "lab_note_generation_time_seconds": lab_note_generation_time,
            "usage_metadata_lab_note_generation": generated_lab_note["usage_metadata"],
            "df_errors": df_errors.to_dict("records"),
            "filtered_dict": filtered_dict,
            "summary_dict": summary_dict,
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


async def evaluate_lab_notes(
    csv_file: str, num_runs: int = 1, output_dir: str = OUTPUT_DIR_DEFAULT
) -> list[dict]:
    """Execute a lab note evaluation.

    This function orchestrates the entire evaluation process. It loads benchmark data from a CSV file,
    iterates through each evaluation set, and performs a specified number of runs for each set.
    The function generates lab notes, analyzes them for errors, and saves the comprehensive
    results in JSON files for each evaluation set and a combined file for all runs.

    Parameters
    ----------
    csv_file : str
        The path to the CSV file containing the benchmark data.
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

    try:
        logger.info("Step 1: Loading benchmark data...")
        df_benchmark_data = pd.read_csv(csv_file)
    except FileNotFoundError:
        logger.exception(
            f"Failed to load CSV file: The file '{csv_file}' was not found."
        )
        raise
    except pd.errors.ParserError:
        logger.exception("Failed to parse CSV file.")
        raise

    try:
        logger.info("Step 2: Creating output directory...")
        Path(output_dir).mkdir(exist_ok=True)
    except OSError:
        logger.exception("Failed to create output directory.")
        raise

    all_results = []
    total_eval_sets = len(df_benchmark_data)

    for index, row in df_benchmark_data.iterrows():
        eval_set_name = row["eval_set_name"]
        logger.info(f"\n{'=' * 60}")
        logger.info(
            f"PROCESSING EVAL SET: {eval_set_name} ({index + 1}/{total_eval_sets})"
        )

        eval_set_results = []

        for run in range(1, num_runs + 1):
            result = _run_single_evaluation(row, eval_set_name, run)
            if result:
                eval_set_results.append(result)

        all_results.extend(eval_set_results)

        if eval_set_results:
            try:
                eval_set_output_file = (
                    Path(output_dir) / f"eval_set_{eval_set_name}_all_runs.json"
                )
                with Path.open(eval_set_output_file, "w") as f:
                    json.dump(eval_set_results, f, indent=2, default=str)
                logger.info(
                    f"Eval set {eval_set_name} results saved to {eval_set_output_file}"
                )
            except Exception:
                logger.exception(f"Failed to save eval set {eval_set_name} results.")

        logger.info(
            f"\nEval set {eval_set_name} completed - {len(eval_set_results)} runs processed successfully"
        )

    try:
        final_output_file = Path(output_dir) / "all_eval_sets_all_runs.json"
        with Path.open(final_output_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        logger.info(f"Final results saved to {final_output_file}")
    except Exception:
        logger.exception("Failed to save final results.")

    logger.info("EVALUATION COMPLETE")
    logger.info(f"Total cases processed: {len(all_results)}")
    logger.info(f"Results saved to: {output_dir}")

    return all_results
