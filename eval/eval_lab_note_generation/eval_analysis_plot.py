"""Plotting functions for analysis of lab note generation evaluation.

This module contains a set of functions for creating various visualizations
based on the evaluation data from lab note generation experiments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

FIGURE_SIZE = (10, 6)
BAR_HEIGHT = 0.8
X_LABEL = "Number of Errors"
GRID_STYLE = {"linestyle": "--", "alpha": 0.7, "color": "lightgray"}
LEGEND_POSITION = {
    "loc": "upper center",
    "bbox_to_anchor": (0.5, -0.15),
    "ncol": 5,
    "frameon": False,
}

DEFAULT_LEGEND_POSITION = {
    "loc": "upper center",
    "bbox_to_anchor": (0.5, -0.15),
    "frameon": False,
}

DEFAULT_GRID_STYLE = {
    "axis": "x",
    "linestyle": "--",
    "linewidth": 0.5,
    "alpha": 0.7,
}


def set_common_style(ax: plt.Axes, max_x_value: int, title: str) -> None:
    """Applies common style elements to plots for consistency.

    Parameters
    ----------
    ax : plt.Axes
        The Matplotlib Axes object to which the style will be applied.
    max_x_value : int
        The maximum value for the x-axis, used to set the x-limit.
    title : str
        The title for the plot.

    """
    ax.set_title(title, fontweight="bold", loc="left")
    ax.set_xlabel(X_LABEL)
    ax.set_xlim(0, max_x_value + 1)
    ax.xaxis.grid(visible=True, **GRID_STYLE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()


def _add_bar_labels(
    ax: plt.Axes,
    params: dict,
    color: str,
    min_width_for_label: int = 2,
) -> None:
    """Helper function to add percentage labels to horizontal bars.

    Parameters
    ----------
    ax : plt.Axes
        The Matplotlib Axes object to add the labels to.
    params: dict
        Dict with y-positions of the bars, widths of the bars (i.e., the counts), starting x-position of each bar, total count for each bar group, used for calculating percentages.
    color : str
        The color of the text label.
    min_width_for_label : int, optional
        The minimum width a bar must have to display a label. Defaults to 2.

    """
    for i, width in enumerate(params["widths"]):
        if width > min_width_for_label and params["total_counts"][i] > 0:
            percentage = round((width / params["total_counts"][i]) * 100)
            ax.text(
                params["start_positions"][i] + width / 2,
                params["y_positions"][i],
                f"{percentage}%",
                va="center",
                ha="center",
                color=color,
                fontweight="bold",
            )


def create_simple_error_chart_bw(
    error_types: list[str],
    total_counts: list[float | int],
    recognized: list[float | int],
    save_path: str | Path,
) -> tuple[plt.Figure, plt.Axes]:
    """Creates a basic error chart with recognized/unrecognized split.

    Parameters
    ----------
    error_types : list[str]
        A list of string labels for each error type.
    total_counts : list[float | int]
        A list of total counts for each error type.
    recognized : list[float | int]
        A list of recognized counts for each error type.
    save_path : str | Path
        The file path to save the generated chart.

    Returns
    -------
    tuple[plt.Figure, plt.Axes]
        A tuple containing the Matplotlib Figure and Axes objects.

    """
    unrecognized = [total - rec for total, rec in zip(total_counts, recognized)]

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    y_pos = np.arange(len(error_types))

    ax.barh(
        y_pos,
        recognized,
        color="#3D4F8C",
        label="Recognized Errors",
        edgecolor="#3D4F8C",
        linewidth=0.5,
    )

    ax.barh(
        y_pos,
        unrecognized,
        left=recognized,
        color="white",
        hatch="///",
        label="Unrecognized Errors",
        edgecolor="#3D4F8C",
        linewidth=0.5,
    )

    label_params = {
        "y_positions": y_pos,
        "widths": recognized,
        "start_positions": np.zeros(len(y_pos)),
        "total_counts": total_counts,
    }
    _add_bar_labels(ax, label_params, "white")
    label_params = {
        "y_positions": y_pos,
        "widths": unrecognized,
        "start_positions": np.array(recognized),
        "total_counts": total_counts,
    }
    _add_bar_labels(ax, label_params, "black")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(
        [f"{err}\n({total})" for err, total in zip(error_types, total_counts)]
    )

    max_x_value = max(total_counts)
    set_common_style(
        ax,
        max_x_value,
        f"Error types (total: {sum(total_counts)}):",
    )

    ax.legend(
        loc=LEGEND_POSITION["loc"],
        bbox_to_anchor=LEGEND_POSITION["bbox_to_anchor"],
        ncol=2,
        frameon=LEGEND_POSITION["frameon"],
    )

    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return fig, ax


def _melt_skill_data(data: list[dict[str, Any]]) -> pd.DataFrame:
    """Helper function to transform skill data into a melted DataFrame for plotting.

    Parameters
    ----------
    data : list[dict[str, Any]]
        A list of dictionaries containing error data with skill breakdowns.

    Returns
    -------
    pd.DataFrame
        A melted DataFrame suitable for plotting with Matplotlib.

    """
    melted_data = []
    for row in data:
        error_type = row["name"]
        total = row["total"]
        for col in row:
            if col not in ["name", "total"]:
                skill, status = col.split("-")
                count = row[col]
                percentage = (count / total) * 100 if total > 0 else 0
                melted_data.append(
                    {
                        "Error Type": error_type,
                        "Total": total,
                        "Skill": skill,
                        "Status": status,
                        "Count": count,
                        "Percentage": percentage,
                    }
                )
    return pd.DataFrame(melted_data)


def _get_color_and_hatch(skill_colors: dict, row: pd.Series) -> tuple[str, str | None]:
    """Determines the color and hatch pattern for a plot bar.

    This helper function takes a DataFrame row and a color map to
    select the appropriate color and a hatch pattern based on the
    "Skill" and "Status" of the data point.

    Parameters
    ----------
    skill_colors : dict
        A dictionary mapping skill names to their corresponding color strings.
    row : pd.Series
        A single row from a DataFrame containing "Skill" and "Status" columns.

    Returns
    -------
    tuple[str, str | None]
        A tuple containing the color string and the hatch pattern string.
        The hatch pattern is '///' if the status is "Unrecognized",
        otherwise it is None.

    """
    color = skill_colors[row["Skill"]]
    hatch = "///" if row["Status"] == "Unrecognized" else None
    return color, hatch


def create_error_chart_skills(
    data: list[dict[str, Any]],
    total_counts: list[float | int],
    save_path: str | Path,
    skill_colors: dict,
) -> tuple[plt.Figure, plt.Axes]:
    """Creates an error chart with a skills breakdown, showing percentages.

    Parameters
    ----------
    data : list[dict[str, Any]]
        A list of dictionaries containing error data with skill breakdowns.
    total_counts : list[float | int]
        A list of total counts for each error type, used for setting the x-axis.
    save_path : str | Path
        The file path to save the generated chart.
    skill_colors : dict
        A dictionary mapping skill names to their corresponding colors.

    Returns
    -------
    tuple[plt.Figure, plt.Axes]
        A tuple containing the Matplotlib Figure and Axes objects.

    """
    min_percentage_for_text = 0
    df = pd.DataFrame(data)
    melted_df = _melt_skill_data(data)

    error_types = df["name"].unique()
    skill_status_combinations = (
        melted_df[["Skill", "Status"]].drop_duplicates().reset_index(drop=True)
    )

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    y_positions = np.arange(len(error_types))
    cumulative_widths = np.zeros(len(error_types))

    for _, row in skill_status_combinations.iterrows():
        skill = row["Skill"]
        status = row["Status"]
        filtered_data = melted_df[
            (melted_df["Skill"] == skill) & (melted_df["Status"] == status)
        ]
        counts_by_error = {
            x["Error Type"]: x["Count"] for _, x in filtered_data.iterrows()
        }
        percentages_by_error = {
            x["Error Type"]: x["Percentage"] for _, x in filtered_data.iterrows()
        }
        widths = [counts_by_error.get(error, 0) for error in error_types]
        color, hatch = _get_color_and_hatch(skill_colors, row)

        ax.barh(
            y_positions,
            widths,
            height=BAR_HEIGHT,
            left=cumulative_widths,
            color=color,
            hatch=hatch,
            edgecolor="white",
            linewidth=0.5,
        )

        for i, (width, cum_width) in enumerate(zip(widths, cumulative_widths)):
            if width > 0:
                error_type = error_types[i]
                percentage = percentages_by_error.get(error_type, 0)
                if percentage >= min_percentage_for_text:
                    text_x = cum_width + width / 2
                    ax.text(
                        text_x,
                        y_positions[i],
                        f"{percentage:.0f}%",
                        ha="center",
                        va="center",
                        color="white",
                        fontweight="bold",
                    )
        cumulative_widths += widths

    ax.set_yticks(y_positions)
    ax.set_yticklabels(
        [
            f"{error_type}\n({df[df['name'] == error_type]['total'].to_numpy()[0]})"
            for error_type in error_types
        ]
    )

    max_x_value = max(total_counts)
    set_common_style(
        ax,
        max_x_value,
        f"Error types by skill (total: {sum(df['total'])}):",
    )

    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return fig, ax


def create_standalone_legend(save_path: str | Path, skill_colors: dict) -> plt.Figure:
    """Creates and saves a standalone legend figure.

    This function is useful for creating a single, separate file that
    can be used as a legend for multiple plots.

    Parameters
    ----------
    save_path : str | Path
        The file path to save the legend figure.
    skill_colors : dict
        A dictionary mapping skill names to their corresponding colors.

    Returns
    -------
    plt.Figure
        The Matplotlib Figure object for the legend.

    """
    legend_fig = plt.figure(figsize=(10, 1.5))
    legend_ax = legend_fig.add_subplot(111)
    legend_ax.axis("off")

    legend_elements = []

    for skill, color in skill_colors.items():
        legend_elements.append(Line2D([0], [0], color=color, lw=8, label=skill))

    legend_elements.append(Line2D([0], [0], color="white", lw=0, label=""))
    legend_elements.append(mpatches.Patch(facecolor="gray", label="Recognized"))
    legend_elements.append(
        mpatches.Patch(facecolor="gray", hatch="///", label="Unrecognized")
    )

    legend_ax.legend(
        handles=legend_elements,
        loc=LEGEND_POSITION["loc"],
        bbox_to_anchor=LEGEND_POSITION["bbox_to_anchor"],
        ncol=LEGEND_POSITION["ncol"],
        frameon=LEGEND_POSITION["frameon"],
    )

    legend_fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(legend_fig)
    return legend_fig


def create_timing_visualization(df_timing: pd.DataFrame, output_dir: Path) -> None:
    """Creates visualizations for timing and cost data.

    This function generates and saves a boxplot of generation times and a
    scatterplot of generation times vs. costs.

    Parameters
    ----------
    df_timing : pd.DataFrame
        A DataFrame containing timing and cost data.
    output_dir : Path
        The directory where the plot will be saved.

    """
    with plt.rc_context({"font.size": 14}):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        df_timing[["generate_time"]].boxplot(ax=ax1)
        ax1.set_ylabel("Time (seconds)")
        ax1.set_title("Generation Times")
        max_time = df_timing["generate_time"].max()
        ax1.set_ylim(bottom=0, top=max_time * 1.1)

        ax2.scatter(df_timing["generate_time"], df_timing["generate_cost"])
        ax2.set_xlabel("generation time (s)")
        ax2.set_ylabel("costs per generation ($)")

        plt.tight_layout()
        plt.savefig(output_dir / "generation_time_statistics.png", dpi=300)
        plt.savefig(output_dir / "generation_time_statistics.pdf", dpi=300)
        plt.close(fig)


def create_cv_boxplot(cv_data: pd.DataFrame, output_dir: Path) -> None:
    """Creates and saves a box plot of the Coefficient of Variation (CV) by metric.

    Parameters
    ----------
    cv_data : pd.DataFrame
        A long-format DataFrame containing the CV values for each metric.
        Must include 'Metric' and 'CV' columns.
    output_dir : Path
        The directory where the plot images will be saved.

    """
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))

    ax = sns.boxplot(data=cv_data, x="Metric", y="CV")
    ax.set_xlabel("performance metric")
    ax.set_ylabel("coefficient of variation (CV)")

    plt.tight_layout()
    plt.savefig(output_dir / "CV_box_plot.png", dpi=300)
    plt.savefig(output_dir / "CV_box_plot.pdf", dpi=300)
    plt.close()


def plot_metrics_with_error_bars(
    experiment_stats: pd.DataFrame, output_dir: Path
) -> None:
    """Creates a bar plot of mean metric scores with error bars for each experiment.

    Parameters
    ----------
    experiment_stats : pd.DataFrame
        A DataFrame with experiments as rows and mean/std metrics as columns,
        as produced by `calculate_descriptive_stats_per_experiment`.
    output_dir : Path
        The directory where the plot images will be saved.

    """
    metrics = [
        col.replace("_mean", "") for col in experiment_stats.columns if "_mean" in col
    ]
    experiment_names = experiment_stats.index.tolist()

    x = np.arange(len(experiment_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ["#43215B", "#1A948E", "#3D4F8C"]

    for i, metric in enumerate(metrics):
        mean_col = f"{metric}_mean"
        std_col = f"{metric}_std"

        means = experiment_stats[mean_col]
        stds = experiment_stats[std_col]

        offset = width * i
        rects = ax.bar(
            x + offset,
            means,
            width,
            label=metric,
            yerr=stds,
            capsize=5,
            color=colors[i % len(colors)],
        )
        ax.bar_label(rects, padding=3, fmt="%.2f")

    ax.set_ylabel("Score")
    ax.set_title("Mean Performance Metrics by Experiment (with Std. Dev. Error Bars)")
    ax.set_xticks(x + width, experiment_names, rotation=45, ha="right")
    ax.legend(loc="upper left", ncols=len(metrics))
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "experiment_metrics_with_error_bars.png", dpi=300)
    plt.savefig(output_dir / "experiment_metrics_with_error_bars.pdf", dpi=300)
    plt.close(fig)


def plot_replicate_performance(replicate_data: pd.DataFrame, output_dir: Path) -> None:
    """Creates a bar plot of mean performance across replicates with error bars.

    This function also overlays a strip plot to show the individual data point
    for each replicate.

    Parameters
    ----------
    replicate_data : pd.DataFrame
        A DataFrame with replicates as rows and mean metric scores as columns,
        as produced by `calculate_replicate_performance`.
    output_dir : Path
        The directory where the plot images will be saved.

    """
    means = replicate_data.mean()
    stds = replicate_data.std()
    metrics = replicate_data.columns.tolist()
    colors = ["#43215B", "#1A948E", "#3D4F8C"]

    fig, ax = plt.subplots(figsize=(6, 6))

    ax.bar(metrics, means, yerr=stds, color=colors, capsize=5, alpha=0.8)

    replicate_data_long = replicate_data.melt(var_name="Metric", value_name="Score")
    sns.stripplot(
        data=replicate_data_long,
        x="Metric",
        y="Score",
        ax=ax,
        color="black",
        jitter=0.1,
        size=8,
        edgecolor="gray",
        linewidth=1,
    )

    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    plt.xticks(rotation=45, ha="right")
    ax.tick_params(axis="y", labelsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, mean_val in enumerate(means):
        ax.text(
            i,
            mean_val + stds[i] + 0.05,
            f"{mean_val:.2f}",
            ha="center",
            va="bottom",
            fontsize=12,
            color="black",
        )

    plt.tight_layout()
    plt.savefig(output_dir / "replicate_performance_summary.png", dpi=300)
    plt.savefig(output_dir / "replicate_performance_summary.pdf", dpi=300)
    plt.close(fig)
