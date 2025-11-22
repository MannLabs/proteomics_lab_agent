"""Helper functions for evaluating the calibration of LLM-as-a-judge."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.container import BarContainer
from scipy.stats import spearmanr

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

PLOT_STYLE = {
    "font.size": 12,
    "font.family": "Arial",
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
}

plt.rcParams.update(PLOT_STYLE)

RATING_KEY_MAP = {
    "Completeness": "completeness_rating",
    "Technical Accuracy": "technical_accuracy_rating",
    "Logical Flow": "logical_flow_rating",
    "Safety": "safety_rating",
    "Formatting": "formatting_rating",
}


def extract_fields(entry: dict, fields: list[str]) -> dict:
    """Extract specific fields from a dictionary entry."""
    return {field: entry[field] for field in fields if field in entry}


def create_markdown_table_from_df(df: pd.DataFrame) -> dict:
    """Converts a DataFrame into a single Markdown table string.

    Includes specific logic for formatting ratings and explanations.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the rating data.

    Returns
    -------
    dict
        Dictionary with success status and the Markdown string in 'data'.

    """
    table_lines = []

    # Define headers
    headers = [
        "Section",
        "Completeness",
        "Technical Accuracy",
        "Logical Flow",
        "Safety",
        "Formatting",
        "Notes",
    ]

    # Add Header row
    table_lines.append(f"| {' | '.join(headers)} |")

    # Add Separator row
    separators = ["---" for _ in headers]
    table_lines.append(f"| {' | '.join(separators)} |")

    for _, row_data in df.iterrows():
        row = [
            clean_md(row_data.get("section", "")),
            get_rating_with_expl(row_data, "completeness"),
            get_rating_with_expl(row_data, "technical_accuracy"),
            get_rating_with_expl(row_data, "logical_flow"),
            get_rating_with_expl(row_data, "safety"),
            get_rating_with_expl(row_data, "formatting"),
            clean_md(row_data.get("notes", "")),
        ]

        table_lines.append(f"| {' | '.join(row)} |")

    return "\n".join(table_lines)


def clean_md(text: str | int) -> str:
    """Removes characters that break Markdown tables."""
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("|", "\\|")  # Escape pipes
    text = text.replace("\n", " ")  # Remove newlines
    return text.strip()


def get_rating_with_expl(row_item: pd.Series, base_name: str) -> str:
    """Formats rating and explanation into a single string."""
    rating = str(row_item.get(f"{base_name}_rating", "N/A"))
    explanation = row_item.get(f"{base_name}_explanation", "")

    if not explanation or pd.isna(explanation):
        return rating

    return f"**{rating}** ({clean_md(explanation)})"


def analyze_rater_agreement(df_llm: pd.DataFrame, df_human: pd.DataFrame) -> dict:
    """Performs correlation analysis between LLM and human raters.

    Parameters
    ----------
    df_llm : pd.DataFrame
        The input DataFrame containing the LLM evaluation results.
    df_human : pd.DataFrame
        The input DataFrame containing the human evaluation results.

    Returns
    -------
    dict
        Dictionary with success status and the correlation results DataFrame.

    """
    if df_llm.empty or df_human.empty:
        return {
            "success": False,
            "message": "One or both input DataFrames are empty.",
            "error_code": "EMPTY_DATA_ERROR",
        }

    try:
        human_clean = df_human.dropna(subset=["protocol_id"]).copy()
        llm_clean = df_llm.dropna(subset=["protocol_id"]).copy()

        rubrics = [
            "Completeness",
            "Technical Accuracy",
            "Logical Flow",
            "Safety",
            "Formatting",
            "Overall",
        ]

        numeric_cols_human = human_clean.select_dtypes(
            include=["float64", "int64"]
        ).columns
        df_human_mean = human_clean.groupby("protocol_id")[numeric_cols_human].mean()

        numeric_cols_llm = llm_clean.select_dtypes(include=["float64", "int64"]).columns
        df_llm_mean = llm_clean.groupby("protocol_id")[numeric_cols_llm].mean()

        df_merged_mean = df_human_mean.merge(
            df_llm_mean, on="protocol_id", suffixes=("_human", "_llm")
        )

        correlation_results = []
        for rubric in rubrics:
            col_human = f"{rubric}_human"
            col_llm = f"{rubric}_llm"

            if col_human in df_merged_mean and col_llm in df_merged_mean:
                spearman_corr, spearman_p = spearmanr(
                    df_merged_mean[col_human], df_merged_mean[col_llm]
                )

                correlation_results.append(
                    {
                        "Rubric": rubric,
                        "Spearman_Correlation": spearman_corr,
                        "Spearman_P_Value": spearman_p,
                    }
                )

        df_corr_results = pd.DataFrame(correlation_results)

    except KeyError:
        logging.exception("Missing expected columns in input DataFrames.")
    except ValueError:
        logging.exception("Value error during correlation calculation.")
    else:
        logging.info("\n--- Correlation Analysis Results ---")
        if not df_corr_results.empty:
            logging.info(df_corr_results.to_markdown(index=False, floatfmt=".4f"))

        return df_corr_results


def visualize_calibration(df_corr_results: pd.DataFrame, output_dir: Path) -> dict:
    """Generates calibration visualizations and saves them to disk.

    Parameters
    ----------
    df_corr_results : pd.DataFrame
        DataFrame containing Spearman correlation results.
    output_dir : Path
        Directory where the plot should be saved.

    """
    try:
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(
            data=df_corr_results,
            x="Rubric",
            y="Spearman_Correlation",
            palette="viridis",
        )
        ax.set_title(
            "Spearman Correlation: Mean Human vs. Mean LLM Raters", fontsize=16
        )
        ax.set_ylabel("Spearman's Correlation", fontsize=12)
        ax.set_xlabel("Rubric", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        plt.savefig(output_dir / "correlation_barchart.pdf")
        logging.info("Generated 'correlation_barchart.pdf'")
        plt.close()

    except (FileNotFoundError, OSError):
        logging.exception("File system error while saving plot.")
    except (KeyError, ValueError):
        logging.exception("Data error prevented plotting.")


def plot_overall_comparison_mean_scores(
    df_human: pd.DataFrame,
    df_llm: pd.DataFrame,
    output_dir: Path,
) -> dict:
    """Create a single grouped bar chart comparing Human vs LLM mean scores.

    This function calculates the overall mean and standard deviation across
    all protocols for both human and LLM raters and plots a single
    comparison chart (for ALL protocols combined).

    Parameters
    ----------
    df_human : pd.DataFrame
        The input DataFrame containing the human evaluation results.
    df_llm : pd.DataFrame
        The input DataFrame containing the LLM evaluation results.
    output_dir : Path
        The directory where the plot images will be saved.

    Returns
    -------
    dict
        Dictionary with success status and paths to the saved files.

    """
    score_columns = [
        "Completeness",
        "Technical Accuracy",
        "Logical Flow",
        "Safety",
        "Formatting",
        "Overall",
    ]

    output_dir.mkdir(parents=True, exist_ok=True)

    means_human = [df_human[col].mean() for col in score_columns]
    stds_human = [df_human[col].std() for col in score_columns]

    means_llm = [df_llm[col].mean() for col in score_columns]
    stds_llm = [df_llm[col].std() for col in score_columns]

    fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(score_columns))
    width = 0.35

    bars_human = ax.bar(
        x - width / 2,
        means_human,
        width,
        yerr=stds_human,
        label="human raters",
        capsize=5,
        alpha=0.8,
        color="#3D4F8C",
        ecolor="black",
    )

    bars_llm = ax.bar(
        x + width / 2,
        means_llm,
        width,
        yerr=stds_llm,
        label="LLM-as-a-judge",
        capsize=5,
        alpha=0.8,
        color="#1A948E",
        ecolor="black",
    )

    add_labels_to_bars(ax, bars_human, means_human, stds_human)
    add_labels_to_bars(ax, bars_llm, means_llm, stds_llm)

    ax.set_title(
        "Overall Mean Score Comparison: All Protocols",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(score_columns, rotation=45, ha="right")
    ax.set_ylabel("Score", fontsize=12)
    ax.grid(visible=True, alpha=0.3, axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend()

    max_y_human = max(
        (m + (s if pd.notna(s) else 0))
        for m, s in zip(means_human, stds_human, strict=False)
        if pd.notna(m)
    )
    max_y_llm = max(
        (m + (s if pd.notna(s) else 0))
        for m, s in zip(means_llm, stds_llm, strict=False)
        if pd.notna(m)
    )

    upper_y_limit = max(max_y_human, max_y_llm, 5.0)
    ax.set_ylim(0, upper_y_limit * 1.15)

    plt.tight_layout()

    filename_png = output_dir / "overall_comparison_mean_scores.png"
    plt.savefig(filename_png, dpi=300, bbox_inches="tight")

    filename_pdf = output_dir / "overall_comparison_mean_scores.pdf"
    plt.savefig(filename_pdf, dpi=300, bbox_inches="tight")

    plt.close(fig)


def add_labels_to_bars(
    ax: plt.Axes,
    bars: BarContainer,
    means: pd.Series | list[float],
    stds: pd.Series | list[float],
) -> None:
    """Adds text labels to a bar chart, positioned above error bars."""
    for bar, mean, std in zip(bars, means, stds, strict=False):
        if pd.notna(mean):
            yval = bar.get_height()
            y_err = std if pd.notna(std) else 0
            text = f"{mean:.2f}"
            # Place text above the error bar
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval + y_err + 0.05,  # Position above error bar
                text,
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )
