"""Protocol Finder Evaluation Set Converter.

This module converts protocol_finder.evalset.json to
protocol_finder_converted.evalset.json format by extracting protocol titles
and video URIs from conversation responses and rewriting the eval cases with
only this information. The converter uses for this the first user response
and the last response overall. The information must be in these part.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import prompt
from dotenv import load_dotenv
from google.genai import Client
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GCS_BUCKET_PATH = os.getenv("GCS_BUCKET_PATH")
BASE_DIR = Path(__file__).parent.parent.parent

EXTRACTION_MODEL = "gemini-2.5-flash"


class Information(BaseModel):
    """Scheme for extracting information results."""

    video_uri: str
    protocol_title: str
    selection_reasoning: str


class ProtocolFinderConverter:
    """Converts evaluation sets from regular to custom format for protocol finder evaluation."""

    def __init__(self):
        """Initialize the converter with a Gemini client."""
        self.client = Client()

    def convert_eval_case(self, eval_case: dict[str, Any]) -> dict[str, Any]:
        """Convert a single eval case from detailed format to custom format.

        Parameters
        ----------
        eval_case : dict[str, Any]
            The evaluation case to convert

        Returns
        -------
        dict[str, Any]
            Converted evaluation case in custom format

        """
        # Extract basic metadata
        eval_id = eval_case.get("eval_id", "")
        session_input = eval_case.get("session_input", {})
        creation_timestamp = eval_case.get("creation_timestamp", 0.0)

        conversation = eval_case.get("conversation", [])
        first_invocation = conversation[0]
        last_invocation = conversation[-1]

        gcs_path, protocol_title = self._extract_video_and_protocol_info(
            first_invocation, last_invocation
        )

        converted_invocation = self._create_converted_invocation(
            first_invocation, gcs_path, protocol_title
        )

        return {
            "eval_id": eval_id,
            "conversation": [converted_invocation],
            "session_input": session_input,
            "creation_timestamp": creation_timestamp,
        }

    def _extract_video_and_protocol_info(
        self, first_invocation: dict[str, Any], last_invocation: dict[str, Any]
    ) -> tuple[str, str]:
        """Extract video GCS path and protocol title from invocations."""
        first_response_text = self._get_first_response_text(first_invocation)
        final_response_text = self._get_final_response_text(last_invocation)

        if first_response_text and final_response_text:
            combined_text = first_response_text + final_response_text
            extracted_information = self.extract_information(combined_text)

            video_uri = extracted_information.video_uri
            filename = Path(video_uri).name
            gcs_path = f"{GCS_BUCKET_PATH}/{filename}"
            protocol_title = extracted_information.protocol_title

            return gcs_path, protocol_title

        return "", ""

    def _create_converted_invocation(
        self, first_invocation: dict[str, Any], gcs_path: str, protocol_title: str
    ) -> dict[str, Any]:
        """Create the converted invocation structure."""
        invocation_id = first_invocation.get("invocation_id", "")
        creation_timestamp_inv = first_invocation.get("creation_timestamp", 0.0)

        user_content = self._create_user_content_part(gcs_path)
        final_response = self._create_final_response_part(protocol_title)

        return {
            "invocation_id": invocation_id,
            "user_content": user_content,
            "final_response": final_response,
            "creation_timestamp": creation_timestamp_inv,
        }

    def _get_first_response_text(self, invocation: dict[str, Any]) -> str:
        """Extract text from the first response in user content."""
        user_content = invocation.get("user_content", {})
        return self._extract_text_from_parts(user_content)

    def _get_final_response_text(self, invocation: dict[str, Any]) -> str:
        """Extract text from the final response of an invocation."""
        final_response = invocation.get("final_response", {})
        return self._extract_text_from_parts(final_response)

    def _extract_text_from_parts(
        self, parts_container: dict[str, Any], parts_key: str = "parts"
    ) -> str:
        """Extract text from a parts container structure.

        Parameters
        ----------
        parts_container : dict[str, Any]
            dictionary containing a parts list
        parts_key : str, optional
            Key name for the parts list, by default "parts"

        Returns
        -------
        str
            Extracted text or empty string if not found

        """
        parts = parts_container.get(parts_key, [])
        if parts and isinstance(parts[0], dict):
            return parts[0].get("text", "")
        return ""

    def extract_information(self, response_text: str) -> Information:
        """Extract protocol titles from response text using LLM.

        Parameters
        ----------
        response_text : str
            The text to extract information from

        Returns
        -------
        Information
            Information object containing extracted video URI, protocol title,
            and selection reasoning

        Raises
        ------
        RuntimeError
            If extraction fails due to API or parsing errors

        """
        try:
            custom_prompt = prompt.EXTRACTION_PROMPT_TEMPLATE.format(
                response_text=response_text
            )
            response = self.client.models.generate_content(
                model=EXTRACTION_MODEL,
                contents=custom_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Information,
                },
            )
            parsed_information: Information = response.parsed
            logger.info("Extracted URI: %s", parsed_information.video_uri)
            logger.info(
                "Extracted protocol title: %s", parsed_information.protocol_title
            )
            logger.info("Reasoning: %s", parsed_information.selection_reasoning)
        except (ValueError, TypeError, AttributeError) as e:
            logger.exception("Error extracting protocol titles")
            raise RuntimeError(f"Failed to extract information: {e}") from e
        else:
            return parsed_information

    def _create_user_content_part(self, gcs_path: str) -> dict[str, Any]:
        """Create the user content part of the invocation."""
        return {
            "parts": [
                self._create_empty_part_with_text(f'Analyse this video: "{gcs_path}".')
            ],
            "role": "user",
        }

    def _create_final_response_part(self, protocol_title: str) -> dict[str, Any]:
        """Create the final response part of the invocation."""
        return {
            "parts": [self._create_empty_part_with_text(protocol_title)],
            "role": None,
        }

    def _create_empty_part_with_text(self, text: str) -> dict[str, Any]:
        """Create a part structure with all fields None except text."""
        return {
            "video_metadata": None,
            "thought": None,
            "inline_data": None,
            "file_data": None,
            "thought_signature": None,
            "code_execution_result": None,
            "executable_code": None,
            "function_call": None,
            "function_response": None,
            "text": text,
        }

    def convert_eval_set(self, input_file: Path, output_file: Path) -> None:
        """Convert an evaluation set from regular format to simplified, custom format.

        Only adds new evaluation cases that don't already exist in the output file.

        Parameters
        ----------
        input_file : Path
            Path to the input evaluation set JSON file
        output_file : Path
            Path where the converted evaluation set will be saved

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        json.JSONDecodeError
            If input file contains invalid JSON
        PermissionError
            If unable to write to output file

        """
        logger.info("Loading evaluation set from: %s", input_file)

        input_eval_set = self._load_input_eval_set(input_file)
        existing_eval_set = self._load_existing_eval_set(output_file)
        existing_eval_ids = self._get_existing_eval_ids(existing_eval_set)

        metadata = self._extract_metadata(input_eval_set, existing_eval_set)

        new_eval_cases, skipped_count = self._process_eval_cases(
            input_eval_set, existing_eval_ids
        )

        self._create_and_save_output(
            existing_eval_set, new_eval_cases, skipped_count, metadata, output_file
        )

    def _load_input_eval_set(self, input_file: Path) -> dict[str, Any]:
        """Load and validate the input evaluation set."""
        try:
            with Path.open(input_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.exception("Input file not found: %s", input_file)
            raise
        except json.JSONDecodeError:
            logging.exception("Invalid JSON in input file")
            raise

    def _load_existing_eval_set(self, output_file: Path) -> dict[str, Any]:
        """Load existing evaluation set from output file if it exists.

        Parameters
        ----------
        output_file : Path
            Path to the output evaluation set file

        Returns
        -------
        dict[str, Any]
            Existing evaluation set or empty structure if file doesn't exist

        """
        if not output_file.exists():
            logger.info(
                "Output file doesn't exist, will create new one: %s", output_file
            )
            return {
                "eval_set_id": "",
                "name": "",
                "description": None,
                "eval_cases": [],
                "creation_timestamp": 0.0,
            }

        try:
            with Path.open(output_file, encoding="utf-8") as f:
                existing_eval_set = json.load(f)
                logger.info(
                    "Loaded existing evaluation set with %d cases",
                    len(existing_eval_set.get("eval_cases", [])),
                )
                return existing_eval_set
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(
                "Error loading existing file %s: %s. Creating new one.", output_file, e
            )
            return {
                "eval_set_id": "",
                "name": "",
                "description": None,
                "eval_cases": [],
                "creation_timestamp": 0.0,
            }

    def _get_existing_eval_ids(self, existing_eval_set: dict[str, Any]) -> set[str]:
        """Get set of existing evaluation case IDs.

        Parameters
        ----------
        existing_eval_set : dict[str, Any]
            Existing evaluation set

        Returns
        -------
        set[str]
            Set of existing evaluation case IDs

        """
        existing_ids = set()
        for eval_case in existing_eval_set.get("eval_cases", []):
            eval_id = eval_case.get("eval_id", "")
            if eval_id:
                existing_ids.add(eval_id)

        logger.info("Found %d existing evaluation case IDs", len(existing_ids))
        return existing_ids

    def _extract_metadata(
        self, input_eval_set: dict[str, Any], existing_eval_set: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract metadata, preferring existing values over input values."""
        return {
            "eval_set_id": existing_eval_set.get("eval_set_id")
            or input_eval_set.get("eval_set_id", ""),
            "name": existing_eval_set.get("name") or input_eval_set.get("name", ""),
            "description": existing_eval_set.get("description")
            or input_eval_set.get("description"),
            "creation_timestamp": existing_eval_set.get("creation_timestamp")
            or input_eval_set.get("creation_timestamp", 0.0),
        }

    def _process_eval_cases(
        self, input_eval_set: dict[str, Any], existing_eval_ids: set[str]
    ) -> tuple[list[dict[str, Any]], int]:
        """Process evaluation cases from input, returning new cases and skip count."""
        input_eval_cases = input_eval_set.get("eval_cases", [])
        new_eval_cases = []
        skipped_count = 0

        logger.info(
            "Processing %d evaluation cases from input...", len(input_eval_cases)
        )

        for i, eval_case in enumerate(input_eval_cases):
            eval_id = eval_case.get("eval_id", "Unknown")

            if self._should_skip_eval_case(
                eval_case, existing_eval_ids, i, len(input_eval_cases)
            ):
                skipped_count += 1
                continue

            logger.info(
                "Processing new eval case %d/%d: %s",
                i + 1,
                len(input_eval_cases),
                eval_id,
            )
            converted_case = self.convert_eval_case(eval_case)
            new_eval_cases.append(converted_case)

        return new_eval_cases, skipped_count

    def _should_skip_eval_case(
        self,
        eval_case: dict[str, Any],
        existing_eval_ids: set[str],
        index: int,
        total_cases: int,
    ) -> bool:
        """Check if an evaluation case should be skipped."""
        eval_id = eval_case.get("eval_id", "Unknown")
        conversation = eval_case.get("conversation", [])

        if not conversation:
            logger.info(
                "Skipping eval case %d/%d: %s (empty conversation)",
                index + 1,
                total_cases,
                eval_id,
            )
            return True

        if eval_id in existing_eval_ids:
            logger.info(
                "Skipping eval case %d/%d: %s (already exists)",
                index + 1,
                total_cases,
                eval_id,
            )
            return True

        return False

    def _create_and_save_output(
        self,
        existing_eval_set: dict[str, Any],
        new_eval_cases: list[dict[str, Any]],
        skipped_count: int,
        metadata: dict[str, Any],
        output_file: Path,
    ) -> None:
        """Create the output evaluation set and save it if there are new cases."""
        all_eval_cases = existing_eval_set.get("eval_cases", []) + new_eval_cases

        output_eval_set = {
            **metadata,
            "eval_cases": all_eval_cases,
        }

        logger.info(
            "Added %d new evaluation cases, skipped %d existing/empty cases",
            len(new_eval_cases),
            skipped_count,
        )
        logger.info("Total evaluation cases in output: %d", len(all_eval_cases))

        if new_eval_cases:
            self._save_output_file(output_eval_set, output_file)
        else:
            logger.info("No new evaluation cases to add. Output file unchanged.")

    def _save_output_file(
        self, output_eval_set: dict[str, Any], output_file: Path
    ) -> None:
        """Save the output evaluation set to file."""
        logger.info("Saving updated evaluation set to: %s", output_file)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with Path.open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_eval_set, f, indent=2, ensure_ascii=False)
            logger.info("Conversion completed successfully!")
        except PermissionError:
            logging.exception("Unable to write to output file")
            raise


def main() -> None:
    """Main entry point for the conversion script.

    Sets up file paths and runs the evaluation set conversion process.
    """
    input_file = BASE_DIR / "proteomics_specialist/protocol_finder.evalset.json"
    output_file = (
        BASE_DIR
        / "eval/eval_video_analyzer_agent/protocol_finder_converted.evalset.json"
    )

    converter = ProtocolFinderConverter()
    converter.convert_eval_set(input_file, output_file)


if __name__ == "__main__":
    main()
