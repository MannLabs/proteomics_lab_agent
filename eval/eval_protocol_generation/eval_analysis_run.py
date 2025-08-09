"""Main analysis pipeline for analysis of protocol generation evaluation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

from eval.eval_lab_note_generation.eval_analysis_data import (
    analyze_timing_and_costs,
    generate_timing_statistics,
    load_json_data,
)

from . import eval_analysis_data as data_manager
from . import eval_analysis_plot as plot_generator
from .eval_analysis_plot import TimingVisualizer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class EvaluationAnalyzer:
    """Analyzes evaluation results from protocol generation experiments.

    This class provides a complete pipeline to process evaluation data from a JSON file, generate various charts and visualizations, and analyze key metrics and timing.
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

    def run_complete_analysis(self, json_file_folder: str | Path) -> dict[str, float]:
        """Runs the complete analysis pipeline for a given JSON file.

        This method orchestrates the entire workflow, from loading data to generating
        charts, analyzing timing, and returning final metrics.

        Parameters
        ----------
        json_file_folder : str | Path
            Path to the JSON file folder containing JSON files with the evaluation results.

        Returns
        -------
        dict[str, float]
            A dictionary containing the final summary metrics.

        """
        all_dataframes = []
        all_json_data = []
        for file in json_file_folder.glob("function_*.json"):
            if file.is_file():
                logging.info(f"Starting analysis of {file}")

                df_without_summary, json_data = self._load_and_process_data(file)
                all_dataframes.append(
                    df_without_summary,
                )
                all_json_data.extend(json_data)

        combined_df = pd.concat(all_dataframes, ignore_index=True)

        self._analysis_plot(combined_df)

        self._analyze_timing_and_costs(all_json_data)

        logging.info("Analysis complete. Results saved to %s", self.output_dir)
        return combined_df["Overall"].mean()

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
        json_data = load_json_data(json_file_path)
        logging.info("Loaded %d evaluation records", len(json_data))

        df_without_summary, df_with_summary = data_manager.process_evaluation_data(
            json_data
        )
        function_name = str(df_with_summary["tested_function_name"].iloc[0])

        df_with_summary.to_csv(
            self.output_dir / f"function_{function_name}_analysis.csv", index=False
        )
        logging.info(f"Saved dataframe for {function_name} function.")
        return df_without_summary, json_data

    def _analyze_timing_and_costs(self, json_data: list[dict[str, Any]]) -> None:
        """Analyzes and visualizes timing and cost data.

        This method processes the raw JSON data to calculate timing and cost
        statistics, saves the results to a CSV file, and generates visualizations.

        Parameters
        ----------
        json_data : list[dict[str, Any]]
            The raw list of dictionaries from the loaded JSON file.

        """
        df_timing = analyze_timing_and_costs(json_data)
        df_timing.to_csv(self.output_dir / "timing_and_costs.csv", index=False)
        generate_timing_statistics(df_timing)
        visualizer = TimingVisualizer(
            df_timing, group_by=["input_type", "function_name"]
        )
        visualizer.create_visualization(self.output_dir)

    def _analysis_plot(self, df: pd.DataFrame) -> None:
        df_copy = df.copy()

        for column_value in [
            "Completeness",
            "Technical Accuracy",
            "Logical Flow",
            "Safety",
            "Formatting",
            "Overall",
        ]:
            plot_generator.plot_line_with_error_bars(
                df_copy, column_value, self.output_dir
            )

        plot_generator.plot_seaborn_individual(df, self.output_dir)

        unique_functions = sorted(df["tested_function_name"].unique())

        for function_name in unique_functions:
            df_filtered = df[df["tested_function_name"] == function_name]
            plot_generator.compare_entries_boxplot(
                df_filtered, "Overall", self.output_dir / f"box_plot_{function_name}"
            )

        plot_generator.create_stacked_bar_chart(df, self.output_dir)
