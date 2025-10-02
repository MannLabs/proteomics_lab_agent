"""Lab note generator agent can convert videos into lab notes by comparing the procedure in videos with existing protocols."""

from __future__ import annotations

import logging
from typing import Literal, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext  # noqa: TC002
from google.genai import types
from pydantic import BaseModel, Field

from proteomics_specialist.config import config
from proteomics_specialist.sub_agents import utils
from proteomics_specialist.sub_agents.enviroment_handling import (
    CloudResourceError,
    EnvironmentValidator,
)

from . import prompt

logging.basicConfig(level=logging.INFO)


def generate_lab_notes(
    query: str,
    tool_context: ToolContext | None,
    protocol_input: Optional[str] = None,  # noqa: UP007 LLM tool call works so far better with optional instead of str | None = None
) -> dict:
    """Generates lab notes by comparing videos with their baseline protocol procedures.

    Parameters
    ----------
    query : str
        Query containing video path and analysis request.
    tool_context : ToolContext | None
        ToolContext containing shared state from the lab_knowledge agent .
    protocol_input : str, optional
        Protocol provided as a string as alternative to provided by ToolContext.

    Returns
    -------
    dict
        A dictionary containing a 'status' and either an 'analysis' or 'error_message'.

    """
    try:
        protocol = None
        if tool_context:
            protocol = tool_context.state.get("retrieved_protocol")
            logging.info("Protocol as ToolContext: %s", protocol)

        if not protocol:
            protocol = protocol_input
            logging.info("Protocol as str input: %s", protocol)

        try:
            env_vars = EnvironmentValidator.load_environment(
                agent_type="lab_note_generator", config=config
            )
        except ValueError as e:
            return {"status": "error", "error_message": str(e)}

        try:
            storage_client, bucket, client = (
                EnvironmentValidator.initialize_cloud_resources(env_vars)
            )
        except CloudResourceError as e:
            return {"status": "error", "error_message": str(e)}

        background_knowledge = utils.generate_parts_from_folder(
            folder_path=env_vars["knowledge_base_path"],
            bucket=bucket,
            subfolder_in_bucket="background_knowledge",
            file_extensions=[".pdf"],
        )

        examples = {
            "protocol": env_vars["example_protocol_path"],
            "video": env_vars["example_video_path"],
            "lab_note": env_vars["example_lab_note_path"],
        }
        example_parts = {}
        for name, path in examples.items():
            example_parts[name] = utils.generate_part_from_path(
                path=path,
                bucket=bucket,
            )

        logging.info(f"query: {query}")
        file_path, filename, message = utils.extract_file_path_and_message(query)
        logging.info(
            f"file_path: {file_path}, filename: {filename}, message: {message}"
        )
        if not file_path:
            return {
                "status": "error",
                "error_message": "Could not extract valid file path from query",
            }

        logging.info("Starting video upload to GCS and conversion to part...")
        video = utils.generate_part_from_path(
            path=file_path,
            bucket=bucket,
            subfolder_in_bucket="input_for_lab_note",
        )
        logging.info(f"Video uploaded and converted successfully: {video['gcs_uri']}")

        logging.info("Generating content...")
        custom_protocol_input_prompt = prompt.ANNOUNCING_INPUT_PROTOCOL_PROMPT.format(
            protocol_input=protocol,
        )
        collected_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt.SYSTEM_PROMPT),
                *background_knowledge["parts"],
                types.Part.from_text(
                    text=prompt.INSTRUCTIONS_LAB_NOTE_GENERATION_PROMPT
                ),
                types.Part.from_text(text=prompt.ANNOUNCING_EXAMPLE_PROTOCOL_PROMPT),
                example_parts["protocol"]["part"],
                types.Part.from_text(text=prompt.ANNOUNCING_EXAMPLE_VIDEO_PROMPT),
                example_parts["video"]["part"],
                types.Part.from_text(text=prompt.ANNOUNCING_EXAMPLE_LAB_NOTE_PROMPT),
                example_parts["lab_note"]["part"],
                types.Part.from_text(text=custom_protocol_input_prompt),
                types.Part.from_text(text=prompt.ANNOUNCING_INPUT_VIDEO_PROMPT),
                video["part"],
                types.Part.from_text(text=prompt.FINAL_INSTRUCTIONS_PROMPT),
            ],
        )
        logging.info(f"Prompt: {collected_content}")

        logging.info("Preparing response...")
        response = client.models.generate_content(
            model=env_vars["model"],
            contents=collected_content,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        logging.info(f"Metadata: {video['metadata']}")
        return {
            "status": "success",
            "local_video_path": file_path,
            "gcs_video_path": video["gcs_uri"],
            "video_name": filename,
            "remaining_message": message,
            "protocol": protocol,
            "lab_notes": response.text,
            "usage_metadata": response.usage_metadata,
            "metadata": video["metadata"] or {},
        }

    except (OSError, ValueError, TypeError, RuntimeError) as e:
        return {"status": "error", "error_message": f"Analysis failed: {e!s}"}


lab_note_generator_agent = LlmAgent(
    name="lab_note_generator_agent",
    model=config.model,
    description="Agent converts video files into lab notes.",
    instruction=f"Always analyse the user query by invoking the tool '{generate_lab_notes.__name__}' and reply the generated response.",
    tools=[generate_lab_notes],
    output_key="lab_notes_result",
)


class StepAnalysis(BaseModel):
    """Individual step analysis in the benchmark dataset."""

    Step: float = Field(
        description="The step number (should be float like 1.0, 11.1, etc.)"
    )
    Benchmark: Literal["Error", "No Error"] = Field(
        description="Whether the step contains an error"
    )
    Class: str = Field(
        default="N/A", description="Class error category if error exists"
    )
    Skill: str = Field(
        default="N/A", description="Skill error category if error exists"
    )


class BenchmarkDataset(BaseModel):
    """Complete benchmark dataset containing analysis of all steps."""

    evaluation_dataset_name: str = Field(description="Name of the evaluation dataset")
    recording_type: Literal["camera", "screen recording"] = Field(
        description="Type of recording used"
    )
    dict_error_classification: list[StepAnalysis] = Field(
        description="List of step analyses with error categories"
    )
    comments: str = Field(description="Additional comments about the analysis")


lab_note_benchmark_helper_agent = LlmAgent(
    name="lab_note_benchmark_helper_agent",
    model=config.model,
    description="Agent helps to generate benchmark dataset from generated lab notes.",
    instruction=prompt.LAB_NOTE_TO_BENCHMARK_DATASET_CONVERSION,
    output_schema=BenchmarkDataset,
)
