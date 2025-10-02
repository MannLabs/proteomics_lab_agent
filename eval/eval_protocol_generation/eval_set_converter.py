"""Converts raw evaluation set JSON files into a structured benchmark CSV.

This module processes conversation logs from an evaluation set, extracts key
information such as video paths, and scientific protocols and compiles the data
into a CSV file. It leverages an LLM for complex contextual information extraction.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import prompt
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from eval.eval_lab_note_generation.eval_set_converter import EvalSetConverter

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent
EXTRACTION_MODEL = "gemini-2.5-flash"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BENCHMARK_CSV_PATH = Path("benchmark_data.csv")
INPUT_JSON_PATH = Path(
    BASE_DIR / "proteomics_lab_agent/protocol_generator.evalset.json"
)
MINIMUM_REQUIRED_FIELDS = ["eval_set_name", "user_prompt", "ground_truth_protocol"]


class UserProtocolRating(BaseModel):
    """Schema for numerical ratings provided by the user."""

    Completeness: float | None
    TechnicalAccuracy: float | None
    LogicalFlow: float | None
    Safety: float | None
    Formatting: float | None


class ExtractedProtocolContent(BaseModel):
    """Schema for content extracted by the LLM."""

    ai_protocol: str | None
    ground_truth_protocol: str | None
    user_prompt: str | None
    user_protocol_rating: UserProtocolRating | None
    comments: str | None
    input_type: str | None
    protocol_type: str | None
    activity_type: str | None


class ProtocoEvalSetConverter(EvalSetConverter):
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
                    "response_schema": ExtractedProtocolContent,
                },
            )
        except Exception:
            logging.exception("LLM call failed.")
            return json.dumps(
                ExtractedProtocolContent(
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

        if eval_id and eval_id in existing_eval_sets:
            logging.info(f"Skipping case ID: {eval_id}. Already exists.")
            return None

        logging.info(f"--- Processing new case ID: {eval_id} ---")

        video_path = self.find_video_path(conversation)

        llm_parsed_data = self.extract_contextual_info_with_llm(conversation)
        llm_data_dict = llm_parsed_data.model_dump()

        video_path = self.find_video_path(conversation)
        if video_path:
            user_prompt = (
                f"""Generate a protocol based on this video \"{video_path}\"."""
            )
        else:
            user_prompt = llm_data_dict.get("user_prompt")

        new_row = {
            "eval_set_name": eval_id,
            "protocol_type": llm_data_dict.get("protocol_type"),
            "activity_type": llm_data_dict.get("activity_type"),
            "user_prompt": user_prompt,
            "input_type": llm_data_dict.get("input_type"),
            "ground_truth_protocol": llm_data_dict.get("ground_truth_protocol"),
            "ai_protocol": llm_data_dict.get("ai_protocol"),
            "user_protocol_rating": llm_data_dict.get("user_protocol_rating"),
            "comments": llm_data_dict.get("comments"),
        }

        logging.info(f"new_row: {new_row}")

        if all(new_row.get(field) for field in MINIMUM_REQUIRED_FIELDS):
            logging.info(f"Finished processing and validated new case '{eval_id}'.")
            return new_row

        logging.warning(
            f"Skipping append for case '{eval_id}'. Missing required fields."
        )
        return None


if __name__ == "__main__":
    if not INPUT_JSON_PATH.exists():
        logging.error(f"Input file not found at: {INPUT_JSON_PATH.resolve()}")
    else:
        converter = ProtocoEvalSetConverter()
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
