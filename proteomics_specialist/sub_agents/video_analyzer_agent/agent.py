"""Video-to-lab-notes agent can convert videos into lab notes based on existing protocols."""
# finds protocol based on list of existing protocols that fits to video content

from __future__ import annotations

import logging

from google.adk.agents import LlmAgent
from google.genai import types

# from google.adk.planners import BuiltInPlanner
from proteomics_specialist.config import config
from proteomics_specialist.sub_agents import utils
from proteomics_specialist.sub_agents.enviroment_handling import (
    CloudResourceError,
    EnvironmentValidator,
)

from . import prompt

logging.basicConfig(level=logging.INFO)


def analyze_proteomics_video(
    query: str,
) -> dict[str, str | dict]:
    """Analyze a proteomics laboratory video.

    Args:
        query: Query containing video path and analysis request

    Returns:
        Dictionary with 'status' and either 'analysis' or 'error_message'

    """
    try:
        try:
            env_vars = EnvironmentValidator.load_environment(
                agent_type="video_analyzer", config=config
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
            file_extensions=["pdf"],
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
        video_results = utils.generate_part_from_path(
            path=file_path,
            bucket=bucket,
            subfolder_in_bucket="input_video",
        )
        logging.info(
            f"Video uploaded and converted successfully: {video_results['gcs_uri']}"
        )

        collected_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt.SYSTEM_PROMPT),
                *background_knowledge["parts"],
                types.Part.from_text(text=prompt.INSTRUCTIONS_VIDEO_ANALYSIS_PROMPT),
                video_results["part"],
                types.Part.from_text(text="User message:"),
                types.Part.from_text(text=message),
                types.Part.from_text(text="Video analysis:"),
            ],
        )

        response = client.models.generate_content(
            model=env_vars["model"],
            contents=collected_content,
            config=types.GenerateContentConfig(temperature=env_vars["temperature"]),
        )

        return {
            "status": "success",
            "local_video_path": file_path,
            "gcs_video_path": video_results["gcs_uri"],
            "video_name": filename,
            "remaining_message": message,
            "video_analysis": response.text,
            "usage_metadata": response.usage_metadata,
        }

    except (OSError, ValueError, TypeError, RuntimeError) as e:
        return {"status": "error", "error_message": f"Analysis failed: {e!s}"}


video_analyzer_agent = LlmAgent(
    name="video_analyzer_agent",
    model=config.model,
    description="Agent analyzes video files.",
    # planner=BuiltInPlanner(
    #     thinking_config=types.ThinkingConfig(include_thoughts=True)
    # ),
    instruction="""Always analyse the user query by invoking the tool 'analyze_proteomics_video' and reply the generated response.""",
    tools=[analyze_proteomics_video],
)
