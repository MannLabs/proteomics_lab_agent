"""Lab note generator agent can convert videos into lab notes by comparing the procedure in videos with existing protocols."""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.adk.agents import LlmAgent
from google.cloud import storage
from google.genai import types

from proteomics_specialist.config import config
from proteomics_specialist.sub_agents import utils

from . import prompt

logging.basicConfig(level=logging.INFO)


def generate_protocols(query: str) -> dict:
    """Generates protocols from input text or videos.

    Parameters
    ----------
    query : str
        Query containing text input or video path and special user request.

    Returns
    -------
    dict
        A dictionary containing a 'status' and either an 'analysis' or 'error_message'.

    """
    try:
        start_time = time.time()
        load_dotenv()

        bucket_name = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        knowledge_base_path = os.getenv("KNOWLEDGE_BASE_PATH")
        example_protocol1_path = os.getenv("EXAMPLE_PROTOCOL1_PATH")
        example_video1_path = os.getenv("EXAMPLE_VIDEO1_PATH")
        example_protocol2_path = os.getenv("EXAMPLE_PROTOCOL2_PATH")
        example_video2_path = os.getenv("EXAMPLE_VIDEO2_PATH")

        model = config.analysis_model
        temperature = config.temperature

        if (
            not bucket_name
            or not project_id
            or not model
            or not temperature
            or not knowledge_base_path
            or not example_protocol1_path
            or not example_video1_path
            or not example_protocol2_path
            or not example_video2_path
        ):
            return {
                "status": "error",
                "error_message": "Missing required environment variables: GOOGLE_CLOUD_STORAGE_BUCKET, GOOGLE_CLOUD_PROJECT, KNOWLEDGE_BASE_PATH, EXAMPLE_PROTOCOL1_PATH, EXAMPLE_VIDEO1_PATH,EXAMPLE_PROTOCOL2_PATH, EXAMPLE_VIDEO2_PATH, config.model, config.temperature",
            }

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        client = genai.Client(vertexai=True, project=project_id, location="us-central1")

        background_knowledge = utils.generate_parts_from_folder(
            folder_path=knowledge_base_path,
            bucket=bucket,
            subfolder_in_bucket="background_knowledge",
            file_extensions=["pdf"],
        )

        logging.info(f"query: {query}")
        file_path, filename, message = utils.extract_file_path_and_message(query)
        logging.info(
            f"file_path: {file_path}, filename: {filename}, message: {message}"
        )
        examples = {
            "protocol1": example_protocol1_path,
            "video1": example_video1_path,
            "protocol2": example_protocol2_path,
            "video2": example_video2_path,
        }
        example_parts = {}
        for name, path in examples.items():
            example_parts[name] = utils.generate_part_from_path(
                path=path,
                bucket=bucket,
            )
        if file_path:
            logging.info("Starting video upload to GCS and conversion to part...")
            video = utils.generate_part_from_path(
                path=file_path,
                bucket=bucket,
                subfolder_in_bucket="input_for_protocol",
            )
            logging.info(
                f"Video uploaded and converted successfully: {video['gcs_uri']}"
            )

            logging.info("Generating content with videos...")
            collected_content = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt.PERSONA_PROMPT),
                    types.Part.from_text(text=prompt.BACKGROUND_KNOWLDGE_PROMPT),
                    *background_knowledge["parts"],
                    types.Part.from_text(
                        text=prompt.INSTRUCTIONS_PROTOCOL_GENERATION_FROM_VIDEO_PROMP
                    ),
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
                    types.Part.from_text(text=prompt.ANNOUNCING_INPUT_VIDEO_PROMPT),
                    video["part"],
                    types.Part.from_text(text=prompt.FINAL_INSTRUCTIONS_PROMPT),
                ],
            )
            gcs_file_path = video["gcs_uri"]

        else:
            logging.info("Could not extract valid file path from query")
            gcs_file_path = None
            file_path = None
            filename = None

            logging.info("Generating content with text input...")
            custom_text_input_prompt = prompt.ANNOUNCING_INPUT_TEXT_PROMPT.format(
                text_input=query,
            )
            collected_content = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt.PERSONA_PROMPT),
                    types.Part.from_text(text=prompt.BACKGROUND_KNOWLDGE_PROMPT),
                    *background_knowledge["parts"],
                    types.Part.from_text(
                        text=prompt.INSTRUCTIONS_PROTOCOL_GENERATION_FROM_TEXT_PROMP
                    ),
                    types.Part.from_text(
                        text=prompt.ANNOUNCING_EXAMPLE_TEXT_TO_PROTOCOL_PROMPT
                    ),
                    example_parts["protocol1"]["part"],
                    types.Part.from_text(text=custom_text_input_prompt),
                ],
            )

        logging.info("Preparing response...")
        response = client.models.generate_content(
            model=model,
            contents=collected_content,
            config=types.GenerateContentConfig(temperature=temperature),
        )

        end_time = time.time()
        protocol_generation_time = end_time - start_time

    except (OSError, ValueError, TypeError, RuntimeError) as e:
        return {"status": "error", "error_message": f"Analysis failed: {e!s}"}

    else:
        return {
            "status": "success",
            "local_video_path": file_path,
            "gcs_video_path": gcs_file_path,
            "video_name": filename,
            "remaining_message": query,
            "protocol": response.text,
            "usage_metadata": response.usage_metadata,
            "protocol_generation_time": protocol_generation_time,
        }


protocol_generator_agent = LlmAgent(
    name="protocol_generator_agent",
    model=config.model,
    description="Agent converts text input or video files into protocols.",
    instruction="Always analyse the user query by invoking the tool 'generate_protocols' and reply the generated response.",
    tools=[generate_protocols],
    output_key="protocol_result",
)
