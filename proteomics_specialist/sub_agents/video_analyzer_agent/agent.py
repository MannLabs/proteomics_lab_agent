"""Video-to-lab-notes agent can convert videos into lab notes based on existing protocols."""
# finds protocol based on list of existing protocols that fits to video content

from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.adk.agents import LlmAgent
from google.cloud import storage
from google.genai import types

# from google.adk.planners import BuiltInPlanner
from proteomics_specialist.config import config
from proteomics_specialist.sub_agents import utils


def analyze_proteomics_video(
    query: str,
) -> dict:
    """Analyze a proteomics laboratory video.

    Args:
        query: Query containing video path and analysis request

    Returns:
        Dictionary with 'status' and either 'analysis' or 'error_message'

    """
    try:
        load_dotenv()
        bucket_name = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        knowledge_base_path = os.getenv("KNOWLEDGE_BASE_PATH")

        model = "gemini-2.5-pro"  # config.model
        temperature = config.temperature

        if (
            not bucket_name
            or not project_id
            or not model
            or not temperature
            or not knowledge_base_path
        ):
            return {
                "status": "error",
                "error_message": "Missing required environment variables: GOOGLE_CLOUD_STORAGE_BUCKET, GOOGLE_CLOUD_PROJECT, KNOWLEDGE_BASE_PATH, config.model, config.temperature",
            }

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        client = genai.Client(vertexai=True, project=project_id, location="us-central1")

        system_prompt = """
        You are Professor Matthias Mann, a pioneering scientist in proteomics and mass spectrometry with extensive laboratory experience. Your scientific reputation was built on exactitude - you cannot help but insist on proper technical terminology and chronological precision in all laboratory documentation.

        # Your background knowledge:
        [These documents are for building your proteomics background knowledge and are not part of your task.]
        """

        instructions_prompt = """
        # Your Task:
        You need to analyze a laboratory video and describe it so that a next agent can find the protocol that best matches the procedure being performed in the video.
        Your analysis must include these verification steps:
        1. Identify the starting state (describe visible features)
        2. List the specific actions taken in sequence while naming the involved equipment
        3. Identify the ending state (describe visible features)
        """

        background_knowledge = utils.generate_parts_from_folder(
            folder_path=knowledge_base_path,
            bucket=bucket,
            subfolder_in_bucket="background_knowledge",
            file_extensions=["pdf"],
        )

        file_path, filename, message = utils.extract_file_path_and_message(query)

        if not file_path:
            return {
                "status": "error",
                "error_message": "Could not extract valid file path from query",
            }

        video_results = utils.generate_part_from_path(
            path=file_path,
            bucket=bucket,
            subfolder_in_bucket="input_video",
        )

        collected_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=system_prompt),
                *background_knowledge["parts"],
                types.Part.from_text(text=instructions_prompt),
                video_results["part"],
                types.Part.from_text(text="User message:"),
                types.Part.from_text(text=message),
                types.Part.from_text(text="Video analysis:"),
            ],
        )

        response = client.models.generate_content(
            model=model,
            contents=collected_content,
            config=types.GenerateContentConfig(temperature=temperature),
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
