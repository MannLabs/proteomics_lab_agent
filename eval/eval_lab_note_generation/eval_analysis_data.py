"""Data manipulation functions for the analysis of lab note generation evaluation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

MEAN_COLS = [
    "Classification Accuracy",
    "Accuracy",
    "Precision (Positive Predictive Value)",
    "Recall (Sensitivity, True Positive Rate)",
    "Specificity (True Negative Rate)",
    "F1 Score",
    "Balanced Accuracy",
    "False Positive Rate",
    "False Negative Rate",
    "False Discovery Rate",
    "False Omission Rate",
    "Positive Predictive Value",
    "Negative Predictive Value",
]

PERFORMANCE_COLS = [
    "inputs_experiment_name",
    "replicate_num",
    "True Positives (TP) = Correct error identifications",
    "True Negatives (TN) = Correct no error identifications",
    "False Positives (FP)",
    "False Negatives (FN)",
    "Total steps evaluated",
    "Errors evaluated",
    "Total errors analyzed",
    "Correctly classified errors",
    *MEAN_COLS,
]

SKILL_TYPES = [
    "SpatialOrientation",
    "SpatialResolution",
    "GeneralKnowledge",
    "Fast",
    "ProteomicsKnowledge",
]

ERROR_TYPES_IDS = ["Omitted", "Error", "Addition", "Deviation", "Deviation & Error"]

ERROR_TYPE_MAPPING = {
    "Omitted": "Omitted",
    "Error": "Error",
    "Deviation": "Deviation in step order",
    "Addition": "Added",
    "Deviation & Error": "Deviation & Error",
}

ERROR_TYPES = [ERROR_TYPE_MAPPING[error_id] for error_id in ERROR_TYPES_IDS]


MODEL_PRICING = {
    "flash_lite": {
        "input": {"text": 0.1, "image": 0.1, "video": 0.1, "audio": 0.3},
        "output": 0.4,
    },
    "gemini-2.0-flash-001": {
        "input": {"text": 0.15, "image": 0.15, "video": 0.15, "audio": 1.0},
        "output": 0.6,
    },
    "gemini-2.5-flash": {
        "input": {"text": 0.30, "image": 0.30, "video": 0.30, "audio": 1.0},
        "output": 2.50,
    },
    "gemini-2.5-pro": {
        "input_low": {
            "text": 1.25,
            "image": 1.25,
            "video": 1.25,
            "audio": 1.25,
        },
        "input_high": {
            "text": 2.5,
            "image": 2.5,
            "video": 2.5,
            "audio": 2.5,
        },
        "output_low": 10,
        "output_high": 15,
    },
}
GEMINI_PRO_HIGH_PRICING_THRESHOLD = 200_000


@dataclass
class ParsedModality:
    """A simple class for modality."""

    value: str


@dataclass
class ParsedTokenDetail:
    """A simple class for token details."""

    modality: ParsedModality
    token_count: int


@dataclass
class ParsedUsageMetadata:
    """A simple class to hold parsed usage metadata."""

    prompt_token_count: int = 0
    candidates_token_count: int = 0
    prompt_tokens_details: list[ParsedTokenDetail] = None


def load_json_data(file_path: str | Path) -> list[dict[str, Any]]:
    """Loads a JSON file from the specified file path.

    Parameters
    ----------
    file_path : str | Path
        The path to the JSON file to be loaded.

    Returns
    -------
    list[dict[str, Any]]
        The data loaded from the JSON file.

    """
    with Path.open(file_path, encoding="utf-8") as file:
        return json.load(file)


def process_evaluation_data(json_data: list[dict[str, Any]]) -> pd.DataFrame:
    """Processes raw JSON data into a structured DataFrame with a summary row.

    Parameters
    ----------
    json_data : list[dict[str, Any]]
        A list of dictionaries containing raw evaluation results.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the processed data and a final summary row.

    """
    rows = []
    for item in json_data:
        row = {
            "inputs_experiment_name": item["eval_set"],
            "replicate_num": item["run"],
        }
        row.update(item["summary_dict"])
        rows.append(row)

    df = pd.DataFrame(rows)
    num_rep = len(df["replicate_num"].unique())

    sum_cols = [col for col in df.columns if col not in MEAN_COLS]
    sum_cols.remove("inputs_experiment_name")
    sum_cols.remove("replicate_num")

    summary_row_data = {
        "inputs_experiment_name": ["Summary"],
        "replicate_num": ["All"],
        **{col: [df[col].sum() / num_rep] for col in sum_cols},
        **{col: [df[col].mean()] for col in MEAN_COLS},
    }

    summary_row = pd.DataFrame(summary_row_data)

    return pd.concat([df, summary_row], ignore_index=True)


def save_dataframe(df_with_summary: pd.DataFrame, output_dir: Path) -> None:
    """Saves processed DataFrames as CSV files.

    This function saves a performance metrics summary and a complete
    analysis DataFrame to the specified output directory.

    Parameters
    ----------
    df_with_summary : pd.DataFrame
        The DataFrame containing processed data and summary metrics.
    output_dir : Path
        The directory where the CSV files will be saved.

    """
    existing_performance_cols = [
        col for col in PERFORMANCE_COLS if col in df_with_summary.columns
    ]
    if existing_performance_cols:
        performance_metrics = df_with_summary[existing_performance_cols]
        performance_metrics.to_csv(output_dir / "performance_metrics.csv", index=False)

    df_with_summary.to_csv(output_dir / "complete_analysis.csv", index=False)
    logging.info(
        f"Saved metrics with {len(existing_performance_cols)} columns to 'performance_metrics.csv'"
    )


def transform_to_data_structure(df_row: pd.Series) -> list[dict[str, Any]]:
    """Transforms a DataFrame row to the required data structure for visualization.

    Parameters
    ----------
    df_row : pd.Series
        A single row from a DataFrame, typically the summary row.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries structured for creating skill-based error charts.

    """
    data = []
    for error_type in ERROR_TYPES_IDS:
        total_column = f"All Type {error_type}"
        total_value = df_row.get(total_column)
        if total_value is None or total_value == 0:
            continue

        display_name = ERROR_TYPE_MAPPING.get(error_type, error_type)
        entry = {"name": display_name, "total": int(total_value)}

        for skill in SKILL_TYPES:
            recognized_col = f"Type {error_type} {skill}"
            all_col = f"All Type {error_type} {skill}"

            recognized_value = int(df_row.get(recognized_col, 0))
            all_value = int(df_row.get(all_col, 0))
            unrecognized_value = all_value - recognized_value

            if recognized_value > 0:
                entry[f"{skill}-Recognized"] = recognized_value
            if unrecognized_value > 0:
                entry[f"{skill}-Unrecognized"] = unrecognized_value

        data.append(entry)

    return data


def calculate_skill_totals(df_row: pd.Series) -> dict[str, float]:
    """Calculates the sum of values for each skill type.

    Parameters
    ----------
    df_row : pd.Series
        A single row from a DataFrame, typically the summary row.

    Returns
    -------
    dict[str, float]
        A dictionary containing the total counts for each skill, split by
        'Type' (recognized) and 'All Type' (all errors).

    """
    results = {}
    for skill in SKILL_TYPES:
        type_sum = 0
        all_type_sum = 0
        for error_type in ERROR_TYPES_IDS:
            type_sum += df_row.get(f"Type {error_type} {skill}", 0)
            all_type_sum += df_row.get(f"All Type {error_type} {skill}", 0)
        results[f"Type {skill}"] = type_sum
        results[f"All Type {skill}"] = all_type_sum
    return results


def parse_usage_metadata_string(usage_str: str) -> ParsedUsageMetadata:
    """Parses a string representation of usage metadata into an object.

    Parameters
    ----------
    usage_str : str
        The string containing the Gemini API usage metadata.

    Returns
    -------
    ParsedUsageMetadata
        An object containing the parsed token counts.

    """
    metadata = ParsedUsageMetadata(prompt_tokens_details=[])

    prompt_match = re.search(r"prompt_token_count=(\d+)", usage_str)
    if prompt_match:
        metadata.prompt_token_count = int(prompt_match.group(1))

    candidates_match = re.search(r"candidates_token_count=(\d+)", usage_str)
    if candidates_match:
        metadata.candidates_token_count = int(candidates_match.group(1))

    modality_pattern = r"ModalityTokenCount\(\s*modality=<MediaModality\.(\w+):\s*\'(\w+)\'>,\s*token_count=(\d+)\s*\)"
    modality_matches = re.findall(modality_pattern, usage_str)

    for match in modality_matches:
        modality_name = match[1]
        token_count = int(match[2])
        metadata.prompt_tokens_details.append(
            ParsedTokenDetail(ParsedModality(modality_name), token_count)
        )

    return metadata


def calculate_gemini_cost(
    usage_metadata: ParsedUsageMetadata, model_type: str = "gemini-2.5-pro"
) -> dict[str, float | str]:
    """Calculates Gemini API costs based on usage metadata and model type.

    Parameters
    ----------
    usage_metadata : ParsedUsageMetadata
        An object containing the parsed token usage.
    model_type : str, optional
        The type of Gemini model used ('gemini-2.5-pro', 'flash_lite', 'gemini-2.5-flash').
        Defaults to 'gemini-2.5-pro'.

    Returns
    -------
    dict[str, Union[float, str]]
        A dictionary containing the cost breakdown and total cost.

    """
    pricing = MODEL_PRICING.get(model_type)
    if not pricing:
        raise ValueError(f"Unknown model type: {model_type}")

    cost_breakdown = {}
    total_cost = 0

    input_tokens_by_modality = {"text": 0, "image": 0, "video": 0, "audio": 0}
    for token_detail in usage_metadata.prompt_tokens_details:
        modality = token_detail.modality.value.lower()
        if modality in input_tokens_by_modality:
            input_tokens_by_modality[modality] = token_detail.token_count

    if model_type == "gemini-2.5-pro":
        use_high_pricing = (
            usage_metadata.prompt_token_count > GEMINI_PRO_HIGH_PRICING_THRESHOLD
        )
        input_prices = (
            pricing["input_high"] if use_high_pricing else pricing["input_low"]
        )
        output_price = (
            pricing["output_high"] if use_high_pricing else pricing["output_low"]
        )
        pricing_tier = "high" if use_high_pricing else "low"
    else:
        input_prices = pricing["input"]
        output_price = pricing["output"]
        pricing_tier = "n/a"

    for modality, tokens in input_tokens_by_modality.items():
        if tokens > 0:
            cost = (tokens / 1_000_000) * input_prices[modality]
            cost_breakdown[f"{modality}_input"] = cost
            total_cost += cost

    output_cost = (usage_metadata.candidates_token_count / 1_000_000) * output_price
    cost_breakdown["text_output"] = output_cost
    total_cost += output_cost

    cost_breakdown["total_input_tokens"] = usage_metadata.prompt_token_count
    cost_breakdown["total_output_tokens"] = usage_metadata.candidates_token_count
    cost_breakdown["total_cost"] = total_cost
    cost_breakdown["model_type"] = model_type
    cost_breakdown["pricing_tier"] = pricing_tier

    return cost_breakdown


def analyze_timing_and_costs(json_data: list[dict[str, Any]]) -> pd.DataFrame:
    """Analyzes timing and cost data from evaluation results.

    Parameters
    ----------
    json_data : list[dict[str, Any]]
        A list of dictionaries containing raw evaluation results.

    Returns
    -------
    pd.DataFrame
        A DataFrame with the timing and cost data for each run.

    """
    timing_data = []

    for item in json_data:
        usage_metadata = parse_usage_metadata_string(item["usage_metadata_generation"])
        if item["model"] is not None:
            cost = calculate_gemini_cost(usage_metadata, item["model"])
        else:
            cost = calculate_gemini_cost(usage_metadata)

        if item["protocol_type"] is not None:
            timing_data.append(
                {
                    "experiment_name": item["eval_set"] + str(item["run"]),
                    "function_name": item["function_name"],
                    "protocol_type": item["protocol_type"],
                    "input_type": item["input_type"],
                    "model": item["model"],
                    "generate_time": item["generation_time_seconds"],
                    "generate_cost": cost["total_cost"],
                }
            )
        else:
            timing_data.append(
                {
                    "experiment_name": item["eval_set"] + str(item["run"]),
                    "generate_time": item["generation_time_seconds"],
                    "generate_cost": cost["total_cost"],
                }
            )

    return pd.DataFrame(timing_data)


def generate_timing_statistics(df_timing: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Generates timing statistics from a timing DataFrame.

    Parameters
    ----------
    df_timing : pd.DataFrame
        A DataFrame containing timing data.

    Returns
    -------
    dict[str, dict[str, float]]
        A dictionary containing key statistics (mean, median, etc.)
        for the generation time.

    """
    return {
        "times": {
            "mean": df_timing["generate_time"].mean(),
            "median": df_timing["generate_time"].median(),
            "std": df_timing["generate_time"].std(),
            "min": df_timing["generate_time"].min(),
            "max": df_timing["generate_time"].max(),
        },
    }
