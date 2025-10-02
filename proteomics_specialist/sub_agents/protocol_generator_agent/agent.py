"""Lab note generator agent can convert videos into lab notes by comparing the procedure in videos with existing protocols."""

from __future__ import annotations

import logging
import time

from google.adk.agents import LlmAgent
from google.genai import types

from proteomics_specialist.config import config
from proteomics_specialist.sub_agents import utils
from proteomics_specialist.sub_agents.enviroment_handling import (
    CloudResourceError,
    EnvironmentValidator,
)

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
        try:
            env_vars = EnvironmentValidator.load_environment(
                agent_type="protocol_generator", config=config
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
        examples = {
            "protocol1": env_vars["example_protocol1_path"],
            "video1": env_vars["example_video1_path"],
            "protocol2": env_vars["example_protocol2_path"],
            "video2": env_vars["example_video2_path"],
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
            metadata = video["metadata"]

        else:
            logging.info("Could not extract valid file path from query")
            gcs_file_path = None
            file_path = None
            filename = None
            metadata = None

            logging.info("Generating content with text input...")
            custom_text_input_prompt = prompt.ANNOUNCING_INPUT_TEXT_PROMPT.format(
                text_input=query,
            )
            word_count = len(query.split())
            metadata = {
                "word_count": str(word_count),
                "input_type": "text",
            }
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
            model=env_vars["model"],
            contents=collected_content,
            config=types.GenerateContentConfig(temperature=env_vars["temperature"]),
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
            "metadata": metadata,
        }


protocol_generator_agent = LlmAgent(
    name="protocol_generator_agent",
    model=config.model,
    description="Agent converts text input or video files into protocols.",
    instruction=f"""
    Path A: If the user provides you with a path or notes, analyze the user query by invoking the tool 'generate_protocols' and reply with the generated response.
    Path B: If the user or model asks you to make corrections to already generated protocols, then apply them without invoking the tool '{generate_protocols.__name__}'.
    """,
    tools=[generate_protocols],
    output_key="protocol_result",
)
