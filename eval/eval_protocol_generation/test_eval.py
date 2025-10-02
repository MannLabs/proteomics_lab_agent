"""Test file for protocol generation evaluation."""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from dotenv import load_dotenv
from google import genai
from google.cloud import storage
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from proteomics_lab_agent.config import config
from proteomics_lab_agent.sub_agents import utils
from proteomics_lab_agent.sub_agents.protocol_generator_agent import agent, prompt

from eval.eval_lab_note_generation.test_eval import setup_logging

from .eval_analysis_run import EvaluationAnalyzer
from .evaluator import evaluate_protocols

if TYPE_CHECKING:
    from typing import Any

    from google.cloud.storage import Bucket

logger = logging.getLogger(__name__)

TEST_THRESHOLD = 4


class InstructionType(str, Enum):
    """Available instruction types for protocol generation."""

    SIMPLE = "simple"
    EXTENDED = "extended"
    NONE = "none"


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log a message with details about the retry attempt."""
    try:
        attempt_number = retry_state.attempt_number
        if retry_state.outcome is not None and retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            logging.info(
                f"Attempt {attempt_number} failed with exception: {exception}. Retry."
            )
    except AttributeError:
        logging.warning("Retry state object missing expected attributes")
    except TypeError:
        logging.warning("Error accessing retry state outcome")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=3, min=60, max=300),
    retry=retry_if_exception_type((ServerError, ClientError, APIError)),
    after=log_retry_attempt,
)
def _generate_content_with_retry(
    client: genai.Client,
    model: str,
    contents: list[types.Part],
    config: types.GenerateContentConfig,
) -> genai.types.GenerateContentResponse:
    """Generate content with automatic retry for server errors."""
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


def _load_environment_variables(
    background_knowledge_path: str | None, *, include_examples: bool
) -> dict[str, str]:
    """Load and validate required environment variables.

    Parameters
    ----------
    background_knowledge_path : str | None
        Path to background knowledge, "default" or "extended"
    include_examples : bool
        Whether examples are needed

    Returns
    -------
    dict[str, str]
        Dictionary of environment variables

    Raises
    ------
    ValueError
        If required environment variables are missing

    """
    load_dotenv()

    env_vars = {
        "bucket_name": os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET"),
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
    }

    if background_knowledge_path == "default":
        env_vars["knowledge_base_path"] = os.getenv("KNOWLEDGE_BASE_PATH")
    elif background_knowledge_path == "extended":
        env_vars["knowledge_base_path"] = os.getenv(
            "EXTENDED_BACKGROUND_KNOWLEDGE_PATH"
        )
    elif background_knowledge_path is not None:
        env_vars["knowledge_base_path"] = background_knowledge_path
    else:
        env_vars["knowledge_base_path"] = None

    if include_examples:
        env_vars.update(
            {
                "example_protocol1_path": os.getenv("EXAMPLE_PROTOCOL1_PATH"),
                "example_video1_path": os.getenv("EXAMPLE_VIDEO1_PATH"),
                "example_protocol2_path": os.getenv("EXAMPLE_PROTOCOL2_PATH"),
                "example_video2_path": os.getenv("EXAMPLE_VIDEO2_PATH"),
            }
        )

    missing_vars = _validate_env_vars(
        env_vars, background_knowledge_path, include_examples=include_examples
    )

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    return env_vars


def _validate_env_vars(
    env_vars: dict[str, str],
    background_knowledge_path: str | None,
    *,
    include_examples: bool,
) -> list[str]:
    """Validate environment variables and return missing ones."""
    missing_vars = []

    if not env_vars["bucket_name"]:
        missing_vars.append("GOOGLE_CLOUD_STORAGE_BUCKET")
    if not env_vars["project_id"]:
        missing_vars.append("GOOGLE_CLOUD_PROJECT")
    if background_knowledge_path is not None and not env_vars["knowledge_base_path"]:
        missing_vars.append("KNOWLEDGE_BASE_PATH")

    if include_examples:
        example_vars = [
            "example_protocol1_path",
            "example_video1_path",
            "example_protocol2_path",
            "example_video2_path",
        ]
        missing_vars.extend(var.upper() for var in example_vars if not env_vars[var])

    return missing_vars


def _setup_clients(env_vars: dict[str, str]) -> tuple[storage.Client, Any, Any]:
    """Setup Google Cloud Storage and GenAI clients.

    Parameters
    ----------
    env_vars : dict[str, str]
        Environment variables dictionary

    Returns
    -------
    tuple
        (storage_client, bucket, genai_client)

    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(env_vars["bucket_name"])
    client = genai.Client(
        vertexai=True, project=env_vars["project_id"], location="us-central1"
    )
    return storage_client, bucket, client


def _load_background_knowledge(
    knowledge_base_path: str | None,
    bucket: Bucket,
) -> dict | None:
    """Load background knowledge from specified path.

    Parameters
    ----------
    knowledge_base_path : str | None
        Path to knowledge base files.
    bucket : Bucket
        Google Cloud Storage bucket

    Returns
    -------
    dict | None
        Background knowledge parts or None if no path specified

    Raises
    ------
    Exception
        If knowledge base loading fails

    """
    if not knowledge_base_path:
        return None

    logging.info(f"Loading background knowledge from: {knowledge_base_path}")

    default_path = os.getenv("KNOWLEDGE_BASE_PATH")
    extended_path = os.getenv("EXTENDED_BACKGROUND_KNOWLEDGE_PATH")

    if knowledge_base_path == default_path:
        subfolder = "background_knowledge"
    elif knowledge_base_path == extended_path:
        subfolder = "extended_background_knowledge"
    else:
        subfolder = "custom_background_knowledge"
        logging.warning(
            f"Using custom background knowledge path: {knowledge_base_path}"
        )

    try:
        return utils.generate_parts_from_folder(
            folder_path=knowledge_base_path,
            bucket=bucket,
            subfolder_in_bucket=subfolder,
            file_extensions=[".pdf"],
        )
    except Exception:
        logging.exception(
            f"Failed to load background knowledge from {knowledge_base_path}."
        )
        raise


def _load_example_parts(
    *, include_examples: bool, env_vars: dict[str, str], bucket: Bucket
) -> dict:
    """Load example protocol and video parts.

    Parameters
    ----------
    include_examples : bool
        Whether to load examples
    env_vars : dict[str, str]
        Environment variables
    bucket : object
        Google Cloud Storage bucket

    Returns
    -------
    dict
        Dictionary of example parts

    """
    if not include_examples:
        return {}

    examples = {
        "protocol1": env_vars["example_protocol1_path"],
        "video1": env_vars["example_video1_path"],
        "protocol2": env_vars["example_protocol2_path"],
        "video2": env_vars["example_video2_path"],
    }

    example_parts = {}
    for name, path in examples.items():
        example_parts[name] = utils.generate_part_from_path(path=path, bucket=bucket)

    return example_parts


def _create_content_builder(
    *,
    include_persona: bool,
    instruction_type: str,
    include_examples: bool,
    knowledge_base_path: str | None,
    background_knowledge: dict | None,
) -> dict[str, Any]:
    """Create content builder configuration."""
    return {
        "include_persona": include_persona,
        "instruction_type": instruction_type,
        "include_examples": include_examples,
        "knowledge_base_path": knowledge_base_path,
        "background_knowledge": background_knowledge,
    }


def _build_content_parts(
    builder_config: dict[str, Any],
    example_parts: dict,
    file_path: str | None,
    query: str,
    bucket: Bucket,
) -> tuple[list, str | None, str | None]:
    """Build the content parts for the AI prompt.

    Parameters
    ----------
    builder_config : dict[str, Any]
        Configuration for content building
    example_parts : dict
        Example parts dictionary
    file_path : str | None
        Path to input file
    query : str
        User query
    bucket : object
        Google Cloud Storage bucket

    Returns
    -------
    tuple
        (content_parts, gcs_file_path, filename)

    """
    content_parts = []

    if builder_config["include_persona"]:
        content_parts.append(types.Part.from_text(text=prompt.PERSONA_PROMPT))

    if builder_config["knowledge_base_path"] and builder_config["background_knowledge"]:
        content_parts.append(
            types.Part.from_text(text=prompt.BACKGROUND_KNOWLDGE_PROMPT)
        )
        content_parts.extend(builder_config["background_knowledge"]["parts"])

    content_parts.extend(
        _get_instruction_parts(builder_config["instruction_type"], file_path)
    )

    if builder_config["include_examples"]:
        content_parts.extend(_get_example_parts(example_parts, file_path))

    gcs_file_path, filename, metadata = _add_input_parts(
        content_parts, file_path, query, bucket
    )

    return content_parts, gcs_file_path, filename, metadata


def _get_instruction_parts(instruction_type: str, file_path: str | None) -> list:
    """Get instruction parts based on type and input method.

    Parameters
    ----------
    instruction_type : str
        Type of instructions
    file_path : str | None
        Input file path

    Returns
    -------
    list
        List of instruction parts

    """
    if instruction_type == "simple":
        if file_path:
            return [
                types.Part.from_text(
                    text=prompt.SIMPLE_INSTRUCTIONS_PROTOCOL_GENERATION_FROM_VIDEO_PROMP
                )
            ]
        return [
            types.Part.from_text(
                text=prompt.SIMPLE_INSTRUCTIONS_PROTOCOL_GENERATION_FROM_TEXT_PROMP
            )
        ]
    if instruction_type == "extended":
        if file_path:
            return [
                types.Part.from_text(
                    text=prompt.INSTRUCTIONS_PROTOCOL_GENERATION_FROM_VIDEO_PROMP
                )
            ]
        return [
            types.Part.from_text(
                text=prompt.INSTRUCTIONS_PROTOCOL_GENERATION_FROM_TEXT_PROMP
            )
        ]
    return []


def _get_example_parts(example_parts: dict, file_path: str | None) -> list:
    """Get example parts based on input method.

    Parameters
    ----------
    example_parts : dict
        Dictionary of example parts
    file_path : str | None
        Input file path

    Returns
    -------
    list
        List of example parts

    """
    if not example_parts:
        return []

    if file_path:
        return [
            types.Part.from_text(text=prompt.ANNOUNCING_EXAMPLE_VIDEO_1_PROMPT),
            example_parts["video1"]["part"],
            types.Part.from_text(
                text=prompt.EXAMPLE_DOCUMENTATION_AND_PROTOCOL_1_PROMPT
            ),
            example_parts["protocol1"]["part"],
            types.Part.from_text(text=prompt.ANNOUNCING_EXAMPLE_VIDEO_2_PROMPT),
            example_parts["video2"]["part"],
            types.Part.from_text(
                text=prompt.EXAMPLE_DOCUMENTATION_AND_PROTOCOL_2_PROMPT
            ),
            example_parts["protocol2"]["part"],
        ]
    return [
        types.Part.from_text(text=prompt.ANNOUNCING_EXAMPLE_TEXT_TO_PROTOCOL_PROMPT),
        example_parts["protocol1"]["part"],
    ]


def _add_input_parts(
    content_parts: list, file_path: str | None, query: str, bucket: Bucket
) -> tuple[str | None, str | None]:
    """Add input parts (video or text) to content parts.

    Parameters
    ----------
    content_parts : list
        List to append input parts to
    file_path : str | None
        Input file path
    query : str
        User query
    bucket : object
        Google Cloud Storage bucket

    Returns
    -------
    tuple
        (gcs_file_path, filename)

    """
    if file_path:
        logging.info("Starting video upload to GCS and conversion to part...")
        video = utils.generate_part_from_path(
            path=file_path,
            bucket=bucket,
            subfolder_in_bucket="input_for_protocol",
        )
        metadata = video["metadata"]
        logging.info(f"Video uploaded and converted successfully: {video['gcs_uri']}")

        content_parts.extend(
            [
                types.Part.from_text(text=prompt.ANNOUNCING_INPUT_VIDEO_PROMPT),
                video["part"],
                types.Part.from_text(text=prompt.FINAL_INSTRUCTIONS_PROMPT),
            ]
        )

        return video["gcs_uri"], utils.extract_file_path_and_message(query)[1], metadata
    logging.info("Could not extract valid file path from query")
    custom_text_input_prompt = prompt.ANNOUNCING_INPUT_TEXT_PROMPT.format(
        text_input=query,
    )
    content_parts.append(types.Part.from_text(text=custom_text_input_prompt))
    word_count = len(query.split())
    metadata = {
        "word_count": str(word_count),
        "input_type": "text",
    }
    return None, None, metadata


@dataclass
class ProtocolConfig:
    """Configuration for protocol generation."""

    include_persona: bool = True
    instruction_type: str = "extended"
    background_knowledge_path: str | None = "default"
    include_examples: bool = True
    model: str = config.analysis_model


def generate_protocols(
    query: str, *, protocol_config: ProtocolConfig | None = None
) -> dict:
    """Generates protocols from input text or videos with configurable content modules.

    Parameters
    ----------
    query : str
        Query containing text input or video path and special user request.
    protocol_config : ProtocolConfig, optional
        Configuration object containing all protocol generation options.
        If None, uses default configuration.

    Returns
    -------
    dict
        A dictionary containing a 'status' and either an 'analysis' or 'error_message'.

    """
    if protocol_config is None:
        protocol_config = ProtocolConfig()

    try:
        start_time = time.time()

        env_vars = _load_environment_variables(
            protocol_config.background_knowledge_path,
            include_examples=protocol_config.include_examples,
        )

        storage_client, bucket, client = _setup_clients(env_vars)

        background_knowledge = _load_background_knowledge(
            env_vars["knowledge_base_path"],
            bucket,
        )

        logging.info(f"query: {query}")
        file_path, filename, message = utils.extract_file_path_and_message(query)
        logging.info(
            f"file_path: {file_path}, filename: {filename}, message: {message}"
        )

        example_parts = _load_example_parts(
            include_examples=protocol_config.include_examples,
            env_vars=env_vars,
            bucket=bucket,
        )

        builder_config = _create_content_builder(
            include_persona=protocol_config.include_persona,
            instruction_type=protocol_config.instruction_type,
            include_examples=protocol_config.include_examples,
            knowledge_base_path=env_vars["knowledge_base_path"],
            background_knowledge=background_knowledge,
        )

        content_parts, gcs_file_path, extracted_filename, metadata = (
            _build_content_parts(
                builder_config, example_parts, file_path, query, bucket
            )
        )

        collected_content = types.Content(role="user", parts=content_parts)
        logging.info(f"Prompt: {collected_content}")

        logging.info("Preparing response...")
        response = _generate_content_with_retry(
            client,
            protocol_config.model,
            collected_content,
            types.GenerateContentConfig(temperature=config.temperature),
        )

        end_time = time.time()
        protocol_generation_time = end_time - start_time

    except ValueError as e:
        return {"status": "error", "error_message": str(e)}
    except (OSError, TypeError, RuntimeError) as e:
        return {"status": "error", "error_message": f"Analysis failed: {e!s}"}
    else:
        return {
            "status": "success",
            "local_video_path": file_path,
            "gcs_video_path": gcs_file_path,
            "video_name": extracted_filename or filename,
            "remaining_message": query,
            "protocol": response.text,
            "usage_metadata": response.usage_metadata,
            "protocol_generation_time": protocol_generation_time,
            "metadata": metadata,
        }


def generate_protocols_regular(query: str) -> dict:
    """Original function - same as full version.

    This is a function with extended instructions, selected background knowledge and examples.
    """
    return agent.generate_protocols(query)


def generate_protocols_with_gemini2_5flash(query: str) -> dict:
    """Function with gemini-2.5-flash."""
    config = ProtocolConfig(model="gemini-2.5-flash")
    return generate_protocols(query, protocol_config=config)


def generate_protocols_with_gemini2_0flash(query: str) -> dict:
    """Function with gemini-2.0-flash and simple instructions."""
    config = ProtocolConfig(
        instruction_type="simple",
        background_knowledge_path=None,
        include_examples=False,
        model="gemini-2.0-flash-001",
    )
    return generate_protocols(query, protocol_config=config)


def generate_protocols_with_simple_inst(query: str) -> dict:
    """Function with simple instructions."""
    config = ProtocolConfig(
        instruction_type="simple",
        background_knowledge_path=None,
        include_examples=False,
    )
    return generate_protocols(query, protocol_config=config)


def generate_protocols_with_examples(query: str) -> dict:
    """Function with simple instructions and examples."""
    config = ProtocolConfig(
        instruction_type="simple",
        background_knowledge_path=None,
        # include_examples=True is default
    )
    return generate_protocols(query, protocol_config=config)


def generate_protocols_with_ext_inst(query: str) -> dict:
    """Function with extended instructions and examples."""
    config = ProtocolConfig(
        background_knowledge_path=None,
    )
    return generate_protocols(query, protocol_config=config)


def generate_protocols_with_ext_know(query: str) -> dict:
    """Function with extended instructions, extensive background knowledge and examples."""
    config = ProtocolConfig(
        background_knowledge_path="extended",
    )
    return generate_protocols(query, protocol_config=config)


def generate_protocols_without_persona(query: str) -> dict:
    """Function without persona but with extended instructions, selected background knowledge and examples."""
    config = ProtocolConfig(include_persona=False)
    return generate_protocols(query, protocol_config=config)


@pytest.mark.asyncio
async def test_protocol_evaluation() -> None:
    """Test lab note evaluation using standalone approach (backward compatibility)."""
    log_file, timestamp = setup_logging()
    logger.info(f"Starting standalone lab note evaluation. Logs: {log_file}")

    try:
        function_configs = [
            # The final experiment for the corresponding paper was conducted using only the standard agent function for protocol generation.
            {"name": "regular", "function": generate_protocols_regular},
            # {
            #     "name": "with_gemini2_0flash",
            #     "function": generate_protocols_with_gemini2_0flash,
            #     "model": "gemini-2.0-flash-001",
            # },
            # {
            #     "name": "with_simple_instructions",
            #     "function": generate_protocols_with_simple_inst,
            # },
            # {
            #     "name": "with_examples",
            #     "function": generate_protocols_with_examples,
            # },
            # {
            #     "name": "with_extended_instructions",
            #     "function": generate_protocols_with_ext_inst,
            # },
            # {
            #     "name": "with_extended_knowledge",
            #     "function": generate_protocols_with_ext_know,
            # },
            # {
            #     "name": "with_gemini2_5flash",
            #     "function": generate_protocols_with_gemini2_5flash,
            #     "model": "gemini-2.5-flash",
            # },
            # {
            #     "name": "without_persona",
            #     "function": generate_protocols_without_persona,
            # },
        ]

        # output_dir = f"./eval_protocol_results/result_20250930_062718"
        output_dir = f"./eval_protocol_results/result_{timestamp}"

        results = await evaluate_protocols(
            csv_file="benchmark_data.csv",
            function_list=function_configs,
            num_runs=3,
            output_dir=output_dir,
        )

        logger.info(
            f"Standalone evaluation completed. Processed {len(results)} total cases"
        )

        analyzer = EvaluationAnalyzer(output_dir)
        metrics = analyzer.run_complete_analysis(Path(output_dir), function_configs)

        assert metrics >= TEST_THRESHOLD, (
            f"Metrics {metrics:.3f} is below minimum threshold of {TEST_THRESHOLD}"
        )
        logger.info(
            f"Metrics {metrics:.3f} meet the minimum threshold of {TEST_THRESHOLD}"
        )

    except Exception:
        logger.exception("Standalone evaluation failed.")
        raise
    finally:
        logging.shutdown()
