"""Plotting functions for analysis of protocol generation evaluation.

This module contains a set of functions for creating various visualizations
based on the evaluation data from protocol generation experiments.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

if TYPE_CHECKING:
    import pandas as pd
    from matplotlib.axes import Axes

LABEL_LENGTH = 20
SHORTEN_LABEL_LENGTH = 50
MAX_RATING = 5.0


class TimingVisualizer:
    """A class to handle timing visualization with better code organization."""

    CUSTOM_COLORS: ClassVar[list[str]] = ["grey", "#43215B", "#1A948E", "#3D4F8C"]
    PLOT_STYLE: ClassVar[dict[str, int]] = {
        "font.size": 12,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
    }

    def __init__(self, df_timing: pd.DataFrame, group_by: list | None = None):
        """Initialize the timing visualization handler.

        Parameters
        ----------
        df_timing : pd.DataFrame
            DataFrame containing timing data to visualize.
        group_by : list or None, optional
            List of column names to group data by. If None, no grouping
            is applied. Default is None.

        """
        self.df_filtered = df_timing.copy()
        self.group_by = group_by
        self.group_column, self.unique_groups = self._setup_grouping()
        self.colors = self._get_colors()

    def _setup_grouping(self) -> tuple[str | None, list | None]:
        """Setup grouping logic."""
        if not self.group_by:
            return None, None

        valid_group_by = [
            col for col in self.group_by if col in self.df_filtered.columns
        ]
        if not valid_group_by:
            logging.info(
                f"Warning: None of the group_by columns {self.group_by} found in DataFrame"
            )
            return None, None

        self.df_filtered["_group_label"] = self.df_filtered[valid_group_by].apply(
            lambda row: " | ".join([f"{col}: {row[col]}" for col in valid_group_by]),
            axis=1,
        )
        return "_group_label", sorted(self.df_filtered["_group_label"].unique())

    def _get_colors(self) -> list:
        """Get appropriate colors for the visualization."""
        if not self.unique_groups:
            return self.CUSTOM_COLORS

        if len(self.unique_groups) <= len(self.CUSTOM_COLORS):
            return self.CUSTOM_COLORS[: len(self.unique_groups)]
        return plt.cm.tab20(np.linspace(0, 1, len(self.unique_groups)))

    def _create_boxplot(self, ax: Axes) -> None:
        """Create the boxplot for generation times."""
        if self.group_column and self.unique_groups:
            box_data = [
                self.df_filtered[self.df_filtered[self.group_column] == group][
                    "generate_time"
                ].to_numpy()
                for group in self.unique_groups
            ]

            bp = ax.boxplot(
                box_data,
                tick_labels=self.unique_groups,
                patch_artist=True,
                showfliers=True,
                flierprops={"marker": "o", "markersize": 4, "alpha": 0.6},
            )

            for patch, color in zip(bp["boxes"], self.colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            for element in ["whiskers", "caps", "medians"]:
                for item in bp[element]:
                    item.set_color("#333333")
                    item.set_linewidth(1.5)

            labels = ax.get_xticklabels()
            if any(len(label.get_text()) > LABEL_LENGTH for label in labels):
                ax.set_xticklabels(labels, rotation=45, ha="right")
        else:
            bp = ax.boxplot(self.df_filtered["generate_time"], patch_artist=True)
            bp["boxes"][0].set_facecolor(self.colors[0])
            bp["boxes"][0].set_alpha(0.7)

        ax.set_ylabel("Time (seconds)", fontweight="bold", fontsize=13)
        ax.set_title("Generation Times", fontweight="bold", fontsize=14, pad=20)

        if not self.df_filtered["generate_time"].empty:
            max_time = self.df_filtered["generate_time"].max()
            ax.set_ylim(bottom=0, top=max_time * 1.15)

    def _create_scatterplot(self, ax: Axes) -> None:
        """Create the scatterplot for generation times vs costs."""
        if self.group_column and self.unique_groups:
            for i, group in enumerate(self.unique_groups):
                mask = self.df_filtered[self.group_column] == group
                ax.scatter(
                    self.df_filtered.loc[mask, "generate_time"],
                    self.df_filtered.loc[mask, "generate_cost"],
                    color=self.colors[i],
                    label=group,
                    alpha=0.8,
                    s=60,
                    edgecolors="white",
                    linewidth=0.8,
                )

            shortened_labels = [
                group[: SHORTEN_LABEL_LENGTH - 3] + "..."
                if len(group) > SHORTEN_LABEL_LENGTH
                else group
                for group in self.unique_groups
            ]

            legend = ax.legend(
                shortened_labels,
                title="Groups",
                bbox_to_anchor=(1.02, 1),
                loc="upper left",
                fontsize=10,
                title_fontsize=11,
            )
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_alpha(0.9)
            legend.get_frame().set_edgecolor("lightgray")
        else:
            ax.scatter(
                self.df_filtered["generate_time"],
                self.df_filtered["generate_cost"],
                c=self.colors[0],
                alpha=0.8,
                s=60,
                edgecolors="white",
                linewidth=0.8,
            )

        ax.set_xlabel("Generation Time (s)", fontweight="bold", fontsize=13)
        ax.set_ylabel("Cost per Generation ($)", fontweight="bold", fontsize=13)
        ax.set_title("Generation Times & Costs", fontweight="bold", fontsize=14, pad=20)

    def _style_axes(self, ax1: Axes, ax2: Axes) -> None:
        """Apply styling to both axes."""
        ax1.set_facecolor("#fafafa")
        ax2.set_facecolor("#fafafa")

    def _get_filename(self) -> str:
        """Generate filename for the saved plot."""
        filename = "generation_time_statistics"
        if self.group_by:
            group_suffix = "_".join(self.group_by)
            filename += f"_by_{group_suffix}"
        return filename

    def create_visualization(self, output_dir: Path) -> None:
        """Create and save the timing visualization."""
        if self.df_filtered.empty:
            logging.warning("Warning: No data to plot")
            return

        plt.style.use("default")

        with plt.rc_context(self.PLOT_STYLE):
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
            fig.patch.set_facecolor("white")

            self._create_boxplot(ax1)
            self._create_scatterplot(ax2)
            self._style_axes(ax1, ax2)

            plt.tight_layout()

            filename = self._get_filename()
            plt.savefig(output_dir / f"{filename}.png", dpi=300, bbox_inches="tight")
            plt.close(fig)


def plot_line_with_error_bars(
    df: pd.DataFrame,
    column_value: str,
    output_dir: Path,
) -> None:
    """Plot line with error bars showing means and standard deviations by configuration.

    Parameters
    ----------
    df : DataFrame
        DataFrame containing the data to plot.
    column_value : str
        Name of the column to plot values for.
    output_dir : Path
        The directory where the plot will be saved.

    """
    configs = df["tested_function_name"].unique()
    means = [
        df[df["tested_function_name"] == config][column_value].mean()
        for config in configs
    ]
    stds = [
        df[df["tested_function_name"] == config][column_value].std()
        for config in configs
    ]

    # Line plot with error bars
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.errorbar(
        range(len(configs)),
        means,
        yerr=stds,
        marker="o",
        markersize=8,
        linewidth=2,
        capsize=5,
        color="teal",
        markerfacecolor="teal",
        markeredgecolor="white",
        ecolor="teal",
        capthick=2,
    )

    for i, config in enumerate(configs):
        y_values = df[df["tested_function_name"] == config][column_value].to_numpy()
        rng = np.random.default_rng()
        x_jitter = rng.normal(i, 0.05, size=len(y_values))
        ax.scatter(
            x_jitter, y_values, alpha=0.4, s=30, marker="x", color="darkslategray"
        )

    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels(configs, rotation=45, ha="right")
    ax.set_ylabel(column_value + " (Rating 1-5)")
    ax.grid(visible=True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_with_error = max([m + s for m, s in zip(means, stds)]) if stds else max(means)
    if max_with_error <= MAX_RATING:
        ax.set_ylim(0, MAX_RATING + 0.1)
    else:
        ax.set_ylim(bottom=0)
    logging.info(
        f"Summary Statistics for {column_value}: {df.groupby('tested_function_name', observed=True)[column_value].describe()[['count', 'mean', 'std']]}"
    )

    plt.tight_layout()
    plt.savefig(
        output_dir / f"line_plot_with_error_bars_{column_value}.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_seaborn_individual(
    df: pd.DataFrame,
    output_dir: str = "./",
    metrics: list | None = None,
) -> None:
    """Create individual plots for each metric using seaborn's bootstrap confidence intervals.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing the data to plot.
    output_dir : str, default "./"
        Directory to save the plots to.
    metrics : list of str or None, default None
        List of metrics to plot. If None, uses default metrics.

    """
    logging.info(f"here: {df['tested_function_name']}")
    if metrics is None:
        metrics = [
            "Overall",
            "Completeness",
            "Technical Accuracy",
            "Logical Flow",
            "Safety",
            "Formatting",
        ]

    # Melt the dataframe to long format for easier plotting
    id_vars = [
        "inputs_experiment_name",
        "replicate_num",
        "tested_function_name",
        "protocol_type",
        "input_type",
        "model",
    ]
    df_melted = df.melt(
        id_vars=id_vars, value_vars=metrics, var_name="metric", value_name="score"
    )

    for metric in metrics:
        fig, ax = plt.subplots(figsize=(14, 8))

        metric_data = df_melted[df_melted["metric"] == metric]

        # Create a categorical x-axis mapping
        unique_functions = df["tested_function_name"].cat.categories.tolist()
        function_mapping = {func: i for i, func in enumerate(unique_functions)}
        metric_data = metric_data.copy()
        metric_data["function_index"] = metric_data["tested_function_name"].map(
            function_mapping
        )

        sns.lineplot(
            data=metric_data,
            x="function_index",
            y="score",
            hue="inputs_experiment_name",
            ax=ax,
            marker="o",
            markersize=8,
            linewidth=3,
            errorbar=("ci", 95),  # 95% bootstrap confidence intervals
            n_boot=1000,
        )  # Number of bootstrap samples

        ax.set_title(
            f"{metric} Performance by Tested Function (Bootstrap 95% CI)",
            fontsize=16,
            fontweight="bold",
        )
        ax.set_xlabel("Tested Function", fontsize=14)
        ax.set_ylabel(f"{metric} Score", fontsize=14)
        ax.set_xticks(range(len(unique_functions)))
        ax.set_xticklabels(unique_functions, rotation=45, ha="right", fontsize=12)
        ax.set_ylim(0, MAX_RATING + 0.1)
        ax.grid(visible=True, alpha=0.3)

        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=12)

        plt.tight_layout()

        filename = f"{output_dir}/Ribbon_plot_{metric}.png"
        fig.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()


def compare_entries_boxplot(
    df: pd.DataFrame, metric: str, output_dir: str = "./"
) -> None:
    """Create box plots comparing all entries using matplotlib."""
    """
    Create box plots comparing all replicate runs using matplotlib.

    Parameters:
    -----------
    df : DataFrame
        DataFrame containing the data to plot.
    metric : str
        metric to plot
    output_dir : str
        directory to save plots

    """

    entry_counts = df["inputs_experiment_name"].value_counts()
    entries_with_pairs = entry_counts[entry_counts > 1].index
    df_paired = df[df["inputs_experiment_name"].isin(entries_with_pairs)]

    if df_paired.empty:
        logging.info("No entries with multiple measurements found!")
        return

    plt.figure(figsize=(14, 8))

    experiment_names = df_paired["inputs_experiment_name"].unique()
    data_for_boxplot = [
        df_paired[df_paired["inputs_experiment_name"] == name][metric].to_numpy()
        for name in experiment_names
    ]

    plt.boxplot(
        data_for_boxplot,
        tick_labels=experiment_names,
        patch_artist=True,
        boxprops={"facecolor": "lightgray"},
    )

    for i, name in enumerate(experiment_names):
        values = df_paired[df_paired["inputs_experiment_name"] == name][metric]
        x_positions = [i + 1] * len(values)  # matplotlib boxplot uses 1-based indexing
        plt.scatter(x_positions, values, color="steelblue", s=64, alpha=0.7, zorder=3)

    plt.xlabel("Protocol Entry", fontsize=12)
    plt.ylabel(metric, fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.grid(visible=True, alpha=0.3, axis="y")
    plt.tight_layout()

    filename = f"{output_dir}_{metric}.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()


def create_stacked_bar_chart(
    df: pd.DataFrame,
    output_dir: str,
    category_col: str = "protocol_type",
    data_col: str = "activity_type",
) -> None:
    """Create a horizontal stacked bar chart from DataFrame data.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame containing the data
    output_dir : str
        directory to save plots
    category_col : str, default 'protocol_type'
        Column name for categories (y-axis labels)
    data_col : str, default 'activity_type'
        Column name for data to stack and count

    """
    data_counts = df.pivot_table(
        index=category_col, columns=data_col, aggfunc="size", fill_value=0
    )
    data_counts = (data_counts > 0).astype(int)  # Convert to binary (0 or 1)
    categories = data_counts.index.tolist()
    activities = data_counts.columns.tolist()

    fig, ax = plt.subplots(figsize=(12, 6))

    default_colors = ["#43215B", "#1A948E", "#3D4F8C", "#E74C3C", "#F39C12", "#27AE60"]
    custom_colors = {
        cat: default_colors[i % len(default_colors)] for i, cat in enumerate(categories)
    }

    hatch_patterns = ["", "///", "\\\\\\", "...", "+++", "xxx", "ooo"]
    labeled_combinations = set()

    for i, category in enumerate(categories):
        left = 0
        category_data = data_counts.loc[category]

        for j, activity in enumerate(activities):
            value = category_data[activity]
            if value > 0:
                # Fix: Define label before using it
                if (category, activity) not in labeled_combinations:
                    label = activity
                    labeled_combinations.add((category, activity))
                else:
                    label = ""

                ax.barh(
                    i,
                    value,
                    left=left,
                    color=custom_colors[category],
                    hatch=hatch_patterns[j % len(hatch_patterns)],
                    edgecolor="black",
                    linewidth=0.5,
                    label=label,
                    alpha=0.8,
                )
                left += value

    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(categories)
    ax.set_xlabel("Count")

    max_count = data_counts.sum(axis=1).max()
    ax.set_xlim(0, max_count * 1.1)
    ax.set_xticks(range(int(max_count) + 1))

    handles, labels = ax.get_legend_handles_labels()
    unique_handles = []
    unique_labels = []
    for handle, label in zip(handles, labels):  # More descriptive variable names
        if label:
            unique_handles.append(handle)
            unique_labels.append(label)

    if unique_handles:
        ax.legend(
            unique_handles[::-1],
            unique_labels[::-1],
            bbox_to_anchor=(1.05, 1),
            loc="upper left",
            title="Activities",
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.3, linestyle="--")

    plt.tight_layout()
    filename = f"{output_dir}/benchmark_dataset.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()
