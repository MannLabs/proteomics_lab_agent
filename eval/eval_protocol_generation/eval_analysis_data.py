"""Data manipulation functions for the analysis of protocol generation evaluation."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def process_evaluation_data(
    json_data: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Processes raw JSON data into a structured DataFrame with a summary row.

    Parameters
    ----------
    json_data : list[dict[str, Any]]
        A list of dictionaries containing raw evaluation results.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        A tuple containing (original_df, df_with_summary).

    """
    if not json_data:
        empty_df = pd.DataFrame()
        return empty_df, empty_df

    non_numeric_cols = {
        "inputs_experiment_name",
        "replicate_num",
        "tested_function_name",
        "protocol_type",
        "activity_type",
        "input_type",
        "model",
    }

    rows = []
    for item in json_data:
        row = {
            "inputs_experiment_name": item["eval_set"],
            "replicate_num": item["run"],
            "tested_function_name": item["function_name"],
            "protocol_type": item["protocol_type"],
            "activity_type": item["activity_type"],
            "input_type": item["input_type"],
            "model": item["model"],
        }
        row.update(item["summary_rating"])
        rows.append(row)

    df = pd.DataFrame(rows)

    numeric_cols = [col for col in df.columns if col not in non_numeric_cols]

    summary_data = {
        "inputs_experiment_name": "Summary",
        "replicate_num": "All",
        "protocol_type": "All",
        "activity_type": "All",
        "input_type": "All",
        "model": "All",
        "tested_function_name": json_data[-1][
            "function_name"
        ],  # Use last item's function name
        **{col: df[col].mean() for col in numeric_cols},
    }

    summary_row = pd.DataFrame([summary_data])
    df_with_summary = pd.concat([df, summary_row], ignore_index=True)

    return df, df_with_summary
