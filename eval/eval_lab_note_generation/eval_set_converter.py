"""Converts raw evaluation set JSON files into a structured benchmark CSV.

This module processes conversation logs from an evaluation set, extracts key
information such as video paths, scientific protocols, and ground truth
lab notes, and compiles the data into a CSV file. It leverages an LLM
for complex contextual information extraction.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pandas as pd
import prompt
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent
EXTRACTION_MODEL = "gemini-2.5-flash"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BENCHMARK_CSV_PATH = Path("benchmark_data.csv")
INPUT_JSON_PATH = Path(
    BASE_DIR / "proteomics_lab_agent/lab_note_generator.evalset.json"
)
MINIMUM_REQUIRED_FIELDS = ["eval_set_name", "protocol", "video_path", "error_dict"]


class ExtractedContent(BaseModel):
    """Schema for content extracted by the LLM."""

    protocol: str | None
    ground_truth_lab_notes: str | None


class EvalSetConverter:
    """Converter class for processing evaluation set JSON files."""

    def __init__(self, minimum_required_fields: list[str] | None = None):
        """Initialize the converter with configuration.

        Parameters
        ----------
        minimum_required_fields : list[str], optional
            List of required fields for validation

        """
        self.minimum_required_fields = (
            minimum_required_fields or MINIMUM_REQUIRED_FIELDS
        )
        self.extraction_model = EXTRACTION_MODEL

    def get_existing_eval_sets(self, csv_path: Path) -> set[str]:
        """Retrieves existing unique evaluation set names from a CSV file.

        Parameters
        ----------
        csv_path : Path
            The path to the benchmark CSV file.

        Returns
        -------
        set[str]
            A set of existing unique evaluation set names.

        """
        if not csv_path.exists():
            return set()
        try:
            df = pd.read_csv(csv_path)
            return set(df["eval_set_name"].dropna().unique())
        except (pd.errors.EmptyDataError, KeyError):
            return set()

    def find_video_path(self, conversation: list[dict]) -> str | None:
        """Finds a GCS video path within a conversation log.

        The function iterates through a conversation to find the first GCS
        URI that matches the video path format.

        Parameters
        ----------
        conversation : list[dict]
            The conversation log, represented as a list of dictionaries.

        Returns
        -------
        str | None
            The found GCS video path as a string, or None if not found.

        """
        for turn in conversation:
            for content_key in ["user_content", "final_response"]:
                parts = turn.get(content_key, {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    if text and (match := re.search(r"gs://[^\s\"]+", text)):
                        return match.group(0)
        return None

    def _find_and_parse_json(self, text: str) -> dict | None:
        """Safely finds and parses a JSON object from a string.

        Parameters
        ----------
        text : str
            The string to search for a JSON object.

        Returns
        -------
        dict | None
            The parsed dictionary, or None if no valid JSON is found.

        """
        logging.info("here")
        try:
            json_str = text.strip()
            if json_str.startswith("{") and json_str.endswith("}"):
                return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def find_benchmark_data(self, conversation: list[dict]) -> dict:
        """Finds and extracts benchmark data from a conversation log.

        The function searches for a JSON object in the conversation, starting from
        the end, that contains a key identifying it as benchmark data.

        Parameters
        ----------
        conversation : list[dict]
            The conversation log, represented as a list of dictionaries.

        Returns
        -------
        dict
            A dictionary containing extracted benchmark data. Returns an empty
            dictionary if no benchmark data is found.

        """
        for turn in reversed(conversation):
            for content_key in ["user_content", "final_response"]:
                parts = turn.get(content_key, {}).get("parts", [{}])
                text = parts[0].get("text", "")
                data = self._find_and_parse_json(text)
                if data and (
                    "evaluation_dataset_name" in data
                    or "dict_error_classification" in data
                ):
                    return {
                        "eval_set_name": data.get("evaluation_dataset_name"),
                        "recording_type": data.get("recording_type"),
                        "error_dict": json.dumps(data.get("dict_error_classification")),
                        "comments": data.get("comments"),
                    }
        return {}

    def extract_contextual_info_with_llm(self, conversation: list[dict]) -> str:
        """Extracts ground truth protocol and lab notes using an LLM.

        The function builds a full conversation log and prompts an LLM to
        extract specific information based on a predefined schema.

        Parameters
        ----------
        conversation : list[dict]
            The conversation log, represented as a list of dictionaries.

        Returns
        -------
        str
            The LLM's response as a JSON string.

        """
        custom_prompt = prompt.EVAL_SET_CONVERTER_PROMPT.format(
            full_conversation_text=conversation
        )

        try:
            client = genai.Client()
            response = client.models.generate_content(
                model=EXTRACTION_MODEL,
                contents=custom_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ExtractedContent,
                },
            )
        except Exception:
            logging.exception("LLM call failed.")
            return json.dumps(
                ExtractedContent(
                    protocol=None, ground_truth_lab_notes=None
                ).model_dump()
            )
        else:
            return response.parsed

    def _process_single_eval_case(
        self, eval_case: dict, existing_eval_sets: set
    ) -> dict | None:
        """Processes a single evaluation case to extract and validate data.

        Parameters
        ----------
        eval_case : dict
            A dictionary representing a single evaluation case.
        existing_eval_sets : set
            A set of evaluation set names that already exist in the benchmark data.

        Returns
        -------
        dict | None
            A dictionary with the extracted data for a new record, or None if the
            case is a duplicate or fails validation.

        """
        eval_id = eval_case.get("eval_id")
        conversation = eval_case.get("conversation", [])
        if not conversation:
            return None

        benchmark_data = self.find_benchmark_data(conversation)

        current_eval_name = benchmark_data.get("eval_set_name")

        if current_eval_name and current_eval_name in existing_eval_sets:
            logging.info(
                f"Skipping case '{current_eval_name}' (ID: {eval_id}). Already exists."
            )
            return None

        logging.info(
            f"--- Processing new case '{current_eval_name}' (ID: {eval_id}) ---"
        )

        video_path = self.find_video_path(conversation)

        if video_path and benchmark_data.get("error_dict"):
            logging.info("Prerequisites met. Calling LLM for contextual extraction.")
            llm_parsed_data = self.extract_contextual_info_with_llm(conversation)
            llm_data_dict = llm_parsed_data.model_dump()

        else:
            llm_data_dict = {}
            logging.warning(
                f"Skipping LLM call for case {eval_id}. Prerequisites not met."
            )

        new_row = {
            "eval_set_name": current_eval_name,
            "protocol": llm_data_dict.get("protocol"),
            "video_path": video_path,
            "recording_type": benchmark_data.get("recording_type"),
            "ground_truth_lab_notes": llm_data_dict.get("ground_truth_lab_notes"),
            "error_dict": benchmark_data.get("error_dict"),
            "comments": benchmark_data.get("comments"),
        }

        logging.info(f"new_row: {new_row}")

        if all(new_row.get(field) for field in MINIMUM_REQUIRED_FIELDS):
            logging.info(
                f"Finished processing and validated new case '{current_eval_name}'."
            )
            return new_row

        logging.warning(
            f"Skipping append for case '{current_eval_name}'. Missing required fields."
        )
        return None

    def extract_data_from_evalset(
        self, filepath: Path, existing_eval_sets: set
    ) -> list[dict]:
        """Extracts data from an evaluation set JSON file.

        This function iterates through all evaluation cases in a JSON file, processes
        each case to extract data, and returns a list of new, valid records.

        Parameters
        ----------
        filepath : Path
            The path to the input JSON file containing evaluation cases.
        existing_eval_sets : set
            A set of existing evaluation set names to prevent duplication.

        Returns
        -------
        list[dict]
            A list of dictionaries, where each dictionary represents a new, valid
            record for the benchmark data.

        """
        with Path.open(filepath, encoding="utf-8") as f:
            eval_set = json.load(f)

        newly_extracted_data = []
        total_cases = len(eval_set.get("eval_cases", []))
        logging.info(
            f"Found {total_cases} total cases. Checking against {len(existing_eval_sets)} existing records."
        )

        for eval_case in eval_set.get("eval_cases", []):
            new_row = self._process_single_eval_case(eval_case, existing_eval_sets)
            if new_row:
                newly_extracted_data.append(new_row)

        return newly_extracted_data


if __name__ == "__main__":
    if not INPUT_JSON_PATH.exists():
        logging.error(f"Input file not found at: {INPUT_JSON_PATH.resolve()}")
    else:
        converter = EvalSetConverter()
        existing_sets = converter.get_existing_eval_sets(BENCHMARK_CSV_PATH)
        new_records = converter.extract_data_from_evalset(
            INPUT_JSON_PATH, existing_sets
        )

        if new_records:
            logging.info(
                f"\nExtracted {len(new_records)} new, valid records to be appended."
            )
            new_df = pd.DataFrame(new_records)
            new_df.to_csv(
                BENCHMARK_CSV_PATH,
                mode="a",
                header=not BENCHMARK_CSV_PATH.exists(),
                index=False,
            )
            logging.info(
                f"Successfully appended new records to '{BENCHMARK_CSV_PATH}'."
            )
        else:
            logging.info("\nNo new, valid records to append.")
