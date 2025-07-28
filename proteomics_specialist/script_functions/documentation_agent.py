"""Documentation agent for converting media to Nature-style protocols using Gemini APIs.

Requirements
-----------
- Google API credentials with sufficient quota (see https://aistudio.google.com/app/apikey)
- Required packages: google-generativeai, gradio
"""

# Native imports
from __future__ import annotations

import base64
import logging
import tempfile
import time
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

# Third-party imports
import google.generativeai as genai
from google.genai import types
from google.generativeai import caching

if TYPE_CHECKING:
    from google.generativeai.types.file_types import File

# Local imports
# Add your local imports here

# Constants
GEMINI_MODEL = "gemini-1.5-flash-001"  # Current production model
GEMINI_PRO_MODEL = (
    "gemini-1.5-pro-001"  # Future upgrade option, not possible with free tier
)
DEFAULT_TIMEOUT = 600  # seconds
DEFAULT_TEMPERATURE = 0

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def _check_timeout(start_time: float, timeout: float | None) -> None:
    """Raises TimeoutError if time exceeds timeout (in seconds)."""
    if timeout and (time.monotonic() - start_time > timeout):
        raise TimeoutError(f"Video processing timed out after {timeout} seconds")


def _check_processing_failed(state_name: str) -> None:
    """Raises ValueError if video processing state is 'FAILED'."""
    if state_name == "FAILED":
        raise ValueError(f"Video processing failed: {state_name}")


def upload_video_and_wait(
    video_path: str,
    check_interval: float = 10.0,
    timeout: float | None = 600.0,
) -> File:
    """Upload a video file and wait for processing completion.

    This function uploads a video file to Google's Generative AI service and
    monitors its processing status until completion or timeout.

    Parameters
    ----------
    video_path : str
        Path to the video file to upload.
    check_interval : float, default=10.0
        Time in seconds between processing status checks.
    timeout : float or None, default=300.0
        Maximum time to wait for processing in seconds. None for no timeout.

    Returns
    -------
    Any
        Processed video file object from Google's Generative AI service.

    Raises
    ------
    FileNotFoundError
        If the video file does not exist.
    ValueError
        If video processing fails.
    TimeoutError
        If processing exceeds the specified timeout.

    """
    file_path = Path(video_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    logger.info("Uploading file: %s", file_path)
    start_time = time.monotonic()

    try:
        video_file = genai.upload_file(path=file_path)
        logger.info("Upload completed. File URI: %s", video_file.uri)

        while video_file.state.name == "PROCESSING":
            _check_timeout(start_time, timeout)
            time.sleep(check_interval)
            video_file = genai.get_file(video_file.name)

        _check_processing_failed(video_file.state.name)
    except Exception:
        logger.exception("Error during video upload/processing")
        raise
    else:
        logger.info("Video processing completed successfully")
        return video_file


def read_and_encode_document(doc_path: str) -> str:
    """Read a document from the specified path and encode it in base64.

    This function reads a file's binary content and converts it to a base64-encoded
    string, which is useful for transmitting binary data as text.

    Parameters
    ----------
    doc_path : str or Path
        Path to the document to be encoded.

    Returns
    -------
    str
        Base64-encoded content of the document as a UTF-8 string.

    Raises
    ------
    FileNotFoundError
        If the specified document path does not exist.

    """
    file_path = Path(doc_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    with Path.open(file_path, "rb") as doc_file:
        content = doc_file.read()
        return base64.b64encode(content).decode("utf-8")


class ProcessingConfig(NamedTuple):
    """Configuration for video processing.

    Parameters
    ----------
    prompts : List[str]
        List of prompts for the model
    video_examples :list[File]
        Processed video file objects from Google's Generative AI service
    file_example : list[dict]
        Encoded content of the example documents
    glossary : dict
        Encoded content of the glossary
    model_name : str
        Name of the Gemini model to use, defaults to GEMINI_MODEL
    cache_display_name : str, optional
        Display name for the cache, defaults to "few_shot_example"
    cache_ttl : timedelta, optional
        Time-to-live for the cache, defaults to 5 minutes

    """

    prompts: list[str]
    video_examples: list[File]
    file_examples: list[dict]
    glossary: dict

    model_name: str = GEMINI_MODEL
    cache_display_name: str = "few_shot_example"
    cache_ttl: timedelta = timedelta(minutes=5)


class CacheStrategy(Enum):
    """Strategy for cache handling during video processing."""

    USE_CACHE = "use_cache"
    BYPASS_CACHE = "bypass_cache"


def process_video(
    video_file: str,
    config: ProcessingConfig,
    cache_strategy: CacheStrategy = CacheStrategy.USE_CACHE,
) -> tuple[str, str]:
    """Process video with or without caching.

    Parameters
    ----------
    video_file : str
        Path to the video file
    config : ProcessingConfig
        Processing configuration
    cache_strategy : CacheStrategy, default=CacheStrategy.USE_CACHE
        Strategy for handling the processing cache. Use CacheStrategy.BYPASS_CACHE
        to skip cache lookup and force reprocessing.

    Returns
    -------
    tuple[str, str]
        (markdown_output, original_filename)

    """
    try:
        processed_video = upload_video_and_wait(video_file)
        if cache_strategy == CacheStrategy.USE_CACHE:
            return _process_with_cache(processed_video, config, video_file)
        return _process_without_cache(processed_video, config, video_file)
    except (OSError, ValueError) as e:
        return f"**Error:** An error occurred during processing: {e!s}"


def _create_cache(config: ProcessingConfig) -> tuple:
    """Create cache with model contents."""
    contents = []

    for video_ex, file_ex in zip(config.video_examples, config.file_examples):
        contents.extend(
            [
                config.prompts[0],
                video_ex,
                config.prompts[1],
                {"mime_type": "text/md", "data": file_ex},
            ]
        )

    contents.extend(
        [
            config.prompts[2],
            {"mime_type": "text/md", "data": config.glossary},
            config.prompts[3],
            config.prompts[4],
        ]
    )

    return caching.CachedContent.create(
        model=config.model_name,
        display_name=config.cache_display_name,
        contents=contents,
        ttl=config.cache_ttl,
    )


def _get_model_inputs(processed_video: File, config: ProcessingConfig) -> list:
    """Get inputs for model processing."""
    contents = []

    # Add each example set with its associated prompts
    for video_ex, file_ex in zip(config.video_examples, config.file_examples):
        contents.extend(
            [
                config.prompts[0],
                video_ex,
                config.prompts[1],
                types.Part.from_bytes(
                    data=file_ex,
                    mime_type="text/md",
                ),
            ]
        )

    # Add glossary, remaining prompts, and processed video
    contents.extend(
        [
            config.prompts[2],
            types.Part.from_bytes(
                data=config.glossary,
                mime_type="text/md",
            ),
            config.prompts[3],
            config.prompts[4],
            processed_video,
            config.prompts[5],
        ]
    )

    return contents


def _generate_response(
    model: genai.GenerativeModel,
    inputs: list,
    timeout: int | None = None,
    video_file: str | None = None,
) -> tuple[str, str]:
    """Generate response from model.

    Parameters
    ----------
    model : genai.GenerativeModel
        Generative model instance
    inputs : List[Any]
        Model inputs
    timeout : Optional[int]
        Request timeout in seconds
    video_file : str, optional
        Path to the video file being processed. Used to extract the original filename.

    Returns
    -------
    tuple[str, str]
        (markdown_output, original_filename)

    """
    request_options = {"timeout": timeout} if timeout else None
    response = model.generate_content(inputs, request_options=request_options)
    logger.info("Model usage metadata: %s", response.usage_metadata)

    original_filename = Path(video_file).stem if video_file else "protocol"

    return response.text, original_filename


def _process_with_cache(
    processed_video: File, config: ProcessingConfig, video_file: str
) -> tuple[str, str]:
    """Handle cached processing.

    Parameters
    ----------
    processed_video : File
        Processed video file
    config : ProcessingConfig
        Processing configuration
    video_file : str
        Path to the video file being processed. Used to extract the original filename.

    Returns
    -------
    tuple[str, str]
        (markdown_output, original_filename)

    """
    cache = _create_cache(config)
    model = genai.GenerativeModel.from_cached_content(cached_content=cache)
    return _generate_response(
        model, [processed_video, config.prompts[5]], video_file=video_file
    )


def _process_without_cache(
    processed_video: File, config: ProcessingConfig, video_file: str
) -> tuple[str, str]:
    """Handle non-cached processing.

    Parameters
    ----------
    processed_video : File
        Processed video file
    config : ProcessingConfig
        Processing configuration
    video_file : str, optional
        Path to the video file being processed. Used to extract the original filename.

    Returns
    -------
    Tuple[str, str]
        (markdown_output, original_filename)

    """
    model = genai.GenerativeModel(
        model_name=config.model_name,
        generation_config=genai.GenerationConfig(temperature=DEFAULT_TEMPERATURE),
    )
    inputs = _get_model_inputs(processed_video, config)

    return _generate_response(
        model, inputs, timeout=DEFAULT_TIMEOUT, video_file=video_file
    )


def _validate_input(text: str, original_filename: str) -> None:
    """Validate the input parameters for markdown generation. Raise ValueError if input parameters are empty."""
    if not text or not original_filename:
        raise ValueError("Text and original_filename cannot be empty")


def generate_markdown_for_download(
    text: str, original_filename: str, temp_dir: str | None = None
) -> Path:
    """Generate a markdown file for download using the original filename.

    This function creates a markdown file in a temporary directory with the
    provided content and returns the path to the created file.

    Parameters
    ----------
    text : str
        The markdown content to write to the file
    original_filename : str
        The original filename to base the markdown filename on
    temp_dir : str | None, optional
        Custom temporary directory path. If None, system temp dir is used

    Returns
    -------
    Path
        Path object pointing to the generated markdown file

    Raises
    ------
    OSError
        If there's an error creating or writing to the file
    ValueError
        If the input parameters are invalid

    """
    try:
        _validate_input(text, original_filename)

        clean_filename = Path(original_filename).stem
        markdown_filename = f"{clean_filename}.md"

        temp_path = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        if not temp_path.exists():
            temp_path.mkdir(parents=True, exist_ok=True)

        file_path = temp_path / markdown_filename

        file_path.write_text(text, encoding="utf-8")

    except OSError:
        logger.exception("Error creating markdown file")
        raise
    except Exception:
        logger.exception("Unexpected error")
        raise
    else:
        logger.info("Created markdown file: %s", file_path)
        return file_path
