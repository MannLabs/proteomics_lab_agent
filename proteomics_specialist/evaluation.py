from __future__ import annotations

# Standard library imports
import json
import logging
import sys
from pathlib import Path

# Type checking imports
from typing import Dict, List, Union

# Third-party imports
import pandas as pd

# Local imports and setup
path_to_append = Path(Path.cwd()).parent / "proteomics_specialist"
sys.path.append(str(path_to_append))
import video_to_protocol

# Type definitions
JSONType = Union[Dict[str, "JSONType"], List["JSONType"], str, int, float, bool, None]

# Configuration
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def get_table_json_prompt(text_with_tables: str, table_identifier: str) -> str:
    """Generates a prompt to extract a specific table from text into JSON.

    Args:
        text_with_tables: The full text containing the table(s).
        table_identifier: A string to help the model identify the target table
                          (e.g., the table title, or a unique phrase near it).

    Returns:
        A formatted prompt string.

    """
    return f"""
    You are an expert data extraction tool.
    Your task is to locate a specific table within the provided text and output its data as a JSON array.

    Here is the text containing the table(s):
    ---TEXT_START---
    {text_with_tables}
    ---TEXT_END---

    Identify the table that best matches the following title: "{table_identifier}"

    It is very important to you to output the data from ONLY this table as a valid JSON array. Each object in the array should represent a row from the table. The keys of each object should be the exact column headers from the identified table.

    Output Constraints:
    - Answer direct with the JSON.
    - If the specified table cannot be found, output an empty JSON array: []
    """


def extract_json_from_model_output(
    model_output_string: str,
) -> Union[pd.DataFrame, None]:
    """Extract and parse JSON data from a model output string that contains JSON within code block markers.

    Parameters
    ----------
    model_output_string : str
        The string output from the model that contains JSON within code block markers

    Returns
    -------
    pd.DataFrame | None
        A pandas DataFrame created from the JSON data, or None if extraction failed

    """
    start_marker = "```json"
    end_marker = "```"

    start_index = model_output_string.find(start_marker)
    end_index = model_output_string.find(
        end_marker, start_index + len(start_marker)
    )  # Search for end marker after the start

    df = None
    if start_index != -1 and end_index != -1:
        extracted_json_string = model_output_string[
            start_index + len(start_marker) : end_index
        ].strip()

        try:
            json_data = json.loads(extracted_json_string)
            logger.info("Successfully extracted and parsed JSON.")

            if isinstance(json_data, list) and all(
                isinstance(item, dict) for item in json_data
            ):
                df = pd.DataFrame(json_data)
            else:
                logger.warning(
                    "JSON data is not a list of dictionaries, could not create DataFrame."
                )
        except json.JSONDecodeError:
            logger.exception("Error decoding JSON after extraction")
            logger.debug(f"Extracted string: {extracted_json_string}")
    else:
        logger.exception("Could not find JSON code block markers in the output.")
        logger.debug(f"Model output: {model_output_string}")

    return df


def extract_table_to_dataframe(
    evaluation: str,
    table_name: str,
    model_name: str = "gemini-2.5-pro-preview-03-25",
    temperature: float = 0.9,
) -> pd.DataFrame:
    """Extract a table from evaluation content and convert it to a DataFrame.

    Parameters
    ----------
    evaluation : str
        The evaluation content containing tables
    table_name : str
        The name of the table to extract
    model_name : str, optional
        The model to use for content generation, default is "gemini-2.5-pro-preview-03-25"
    temperature : float, optional
        Temperature setting for content generation, default is 0.9

    Returns
    -------
    pd.DataFrame
        DataFrame containing the extracted table data

    """
    """Extract a table from evaluation content and convert it to a DataFrame.

    Parameters
    ----------
    evaluation : str
        The evaluation content containing tables
    table_name : str
        The name of the table to extract
    model_name : str, optional
        The model to use for content generation, default is "gemini-2.5-pro-preview-03-25"
    temperature : float, optional
        Temperature setting for content generation, default is 0.9

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the extracted table data

    """
    extraction_prompt = get_table_json_prompt(evaluation, table_name)

    json_response, _ = video_to_protocol.generate_content_from_model(
        extraction_prompt, model_name=model_name, temperature=temperature
    )

    return extract_json_from_model_output(json_response)
