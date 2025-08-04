"""Main analysis pipeline for analysis of lab note generation evaluation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

from . import eval_analysis_data as data_manager
from . import eval_analysis_plot as plot_generator
from .eval_analysis_data import SKILL_TYPES

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

ALL_TYPE_PREFIX = "All Type "
RECOGNIZED_TYPE_PREFIX = "Type "


class EvaluationAnalyzer:
    """Analyzes evaluation results from lab note generation experiments.

    This class provides a complete pipeline to process evaluation data from a JSON file,
    generate various charts and visualizations, and analyze key metrics and timing.
    """

    def __init__(self, output_dir: str | Path = "results"):
        """Initializes the analyzer with output directory and plotting configurations.

        Parameters
        ----------
        output_dir : str | Path, optional
            The directory where all analysis results will be saved.
            Defaults to 'results'.

        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        mpl.rcParams["font.family"] = "Arial"
        mpl.rcParams["pdf.fonttype"] = 42
        plt.rcParams.update({"font.size": 14})

        self.skill_colors = {
            "GeneralKnowledge": "grey",
            "ProteomicsKnowledge": "#43215B",
            "SpatialOrientation": "#00F777C8",
            "SpatialResolution": "#1A948E",
            "Fast": "#3D4F8C",
        }

    def run_complete_analysis(self, json_file_path: str | Path) -> dict[str, float]:
        """Runs the complete analysis pipeline for a given JSON file.

        This method orchestrates the entire workflow, from loading data to generating
        charts, analyzing timing, and returning final metrics.

        Parameters
        ----------
        json_file_path : str | Path
            Path to the JSON file containing the evaluation results.

        Returns
        -------
        dict[str, float]
            A dictionary containing the final summary metrics, including 'Accuracy',
            'Precision (Positive Predictive Value)', and 'Recall (Sensitivity, True Positive Rate)'.

        """
        logging.info(f"Starting analysis of {json_file_path}")

        df_with_summary, json_data = self._load_and_process_data(json_file_path)

        self._generate_error_and_skill_charts(df_with_summary)

        self._analyze_timing_and_costs(json_data)

        final_metrics = self._get_final_metrics(df_with_summary)
        logging.info("Analysis complete. Results saved to %s", self.output_dir)
        return final_metrics

    def _load_and_process_data(
        self, json_file_path: str | Path
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """Loads evaluation data from a JSON file and processes it into a DataFrame.

        Parameters
        ----------
        json_file_path : str | Path
            Path to the JSON file containing evaluation results.

        Returns
        -------
        tuple[pd.DataFrame, list[dict[str, Any]]]
            A tuple containing the processed DataFrame and the raw JSON data.

        """
        json_data = data_manager.load_json_data(json_file_path)
        logging.info("Loaded %d evaluation records", len(json_data))

        df_with_summary = data_manager.process_evaluation_data(json_data)
        data_manager.save_dataframe(df_with_summary, self.output_dir)
        return df_with_summary, json_data

    def _get_available_columns(
        self, df: pd.DataFrame, base_names: list[str], prefix: str
    ) -> list[str]:
        """A helper method to find available columns in a DataFrame based on a prefix."""
        return [
            f"{prefix}{name}" for name in base_names if f"{prefix}{name}" in df.columns
        ]

    def _generate_error_and_skill_charts(self, df_with_summary: pd.DataFrame) -> None:
        """Generate charts for error types and skill recognition."""
        last_row = df_with_summary.iloc[-1]

        data = data_manager.transform_to_data_structure(last_row)
        if not data:
            logging.info(
                "Warning: No data found for visualization. Skipping chart generation."
            )
            return

        error_types_filtered = [item["name"] for item in data]
        total_counts = [item["total"] for item in data]

        recognized = []
        for item in data:
            recognized_count = 0
            for key, value in item.items():
                if key.endswith("-Recognized"):
                    recognized_count += value
            recognized.append(recognized_count)

        plot_generator.create_simple_error_chart_bw(
            error_types_filtered,
            total_counts,
            recognized,
            self.output_dir / "error_types_chart.png",
        )

        plot_generator.create_error_chart_skills(
            data,
            total_counts,
            self.output_dir / "error_types_by_skill_recognition.png",
            self.skill_colors,
        )

        plot_generator.create_standalone_legend(
            self.output_dir / "legend.png", self.skill_colors
        )

        skill_totals = data_manager.calculate_skill_totals(last_row)
        skill_totals_df = pd.DataFrame([skill_totals])

        all_type_skill_cols = self._get_available_columns(
            skill_totals_df, SKILL_TYPES, ALL_TYPE_PREFIX
        )
        type_skill_cols = self._get_available_columns(
            skill_totals_df, SKILL_TYPES, RECOGNIZED_TYPE_PREFIX
        )

        if all_type_skill_cols and type_skill_cols:
            skill_types_filtered = [
                col.replace(ALL_TYPE_PREFIX, "") for col in all_type_skill_cols
            ]
            all_counts = skill_totals_df[all_type_skill_cols].iloc[0]
            recognized_counts = skill_totals_df[type_skill_cols].iloc[0]

            plot_generator.create_simple_error_chart_bw(
                skill_types_filtered,
                all_counts,
                recognized_counts,
                self.output_dir / "skill_types_chart_bw.png",
            )

    def _analyze_timing_and_costs(self, json_data: list[dict[str, Any]]) -> None:
        """Analyzes and visualizes timing and cost data.

        This method processes the raw JSON data to calculate timing and cost
        statistics, saves the results to a CSV file, and generates visualizations.

        Parameters
        ----------
        json_data : list[dict[str, Any]]
            The raw list of dictionaries from the loaded JSON file.

        """
        df_timing = data_manager.analyze_timing_and_costs(json_data)
        df_timing.to_csv(self.output_dir / "timing_and_costs.csv", index=False)
        data_manager.generate_timing_statistics(df_timing)
        plot_generator.create_timing_visualization(df_timing, self.output_dir)

    def _get_final_metrics(self, df_with_summary: pd.DataFrame) -> dict[str, float]:
        """Extracts and returns the final evaluation metrics from the summary DataFrame.

        Parameters
        ----------
        df_with_summary : pd.DataFrame
            The processed DataFrame containing the summary data.

        Returns
        -------
        dict[str, float]
            A dictionary of key metrics from the last row of the DataFrame.
            Returns an empty dictionary if the metrics are not found.

        """
        metrics_cols = [
            "Accuracy",
            "Precision (Positive Predictive Value)",
            "Recall (Sensitivity, True Positive Rate)",
        ]

        available_metrics = [
            col for col in metrics_cols if col in df_with_summary.columns
        ]

        if not available_metrics:
            logging.warning("Required metrics not found in summary DataFrame.")
            return {}

        return df_with_summary[available_metrics].iloc[-1].to_dict()
