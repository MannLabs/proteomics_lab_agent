"""Documentation agent for converting media to Nature-style protocols using Gemini APIs.

Requirements
-----------
- Google API credentials with sufficient quota (see https://aistudio.google.com/app/apikey)
- Required packages: google-generativeai, gradio
"""

# Native imports
from datetime import datetime, timedelta
import base64
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, List, Optional, Union, NamedTuple, Tuple

# Third-party imports
from IPython.display import display, Markdown
import google.generativeai as genai
from google.generativeai import caching
import gradio as gr

# Local imports
# Add your local imports here

# Constants
GEMINI_MODEL = "gemini-1.5-flash-001"  # Current production model
GEMINI_PRO_MODEL = "gemini-1.5-pro-001"  # Future upgrade option, not possible with free tier
DEFAULT_TIMEOUT = 600  # seconds

# toDO: Add secret for api_key

def upload_video_and_wait(
    video_path: str,
    check_interval: float = 10.0,
    timeout: Optional[float] = 300.0,
) -> Any:
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
    
    print(f"Uploading file: {file_path}")
    start_time = time.monotonic()
    
    try:
        video_file = genai.upload_file(path=file_path)
        print(f"Upload completed. File URI: {video_file.uri}")
        
        while video_file.state.name == "PROCESSING":
            if timeout and (time.monotonic() - start_time > timeout):
                raise TimeoutError(f"Video processing timed out after {timeout} seconds")
                
            print(".", end="", flush=True)
            time.sleep(check_interval)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            raise ValueError(f"Video processing failed: {video_file.state.name}")
            
        print("\nVideo processing completed successfully")
        return video_file
        
    except Exception as e:
        print(f"\nError during video upload/processing: {str(e)}")
        raise


def read_and_encode_document(
    doc_path: str
) -> str:
    """
    Read a document from the specified path and encode it in base64.

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
    PermissionError
        If the program lacks permission to read the file.
    IOError
        If there's an error reading the file.
    """
    file_path = Path(doc_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")
        
    try:
        with open(file_path, "rb") as doc_file:
            content = doc_file.read()
            return base64.b64encode(content).decode("utf-8")
    except PermissionError as e:
        raise PermissionError(f"Permission denied accessing file: {file_path}") from e
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {str(e)}") from e


class ProcessingConfig(NamedTuple):
    """Configuration for video processing.
    
    Parameters
    ----------
    prompts : List[str]
        List of prompts for the model
    video_example : Any
        Processed video file object from Google's Generative AI service
    file_example : dict
        Encoded content of the example document
    glossary : dict
        Encoded content of the glossary
    model_name : str
        Name of the Gemini model to use, defaults to GEMINI_MODEL
    cache_display_name : str, optional
        Display name for the cache, defaults to "few_shot_example"
    cache_ttl : timedelta, optional
        Time-to-live for the cache, defaults to 5 minutes
    """

    prompts: List[str]
    video_example: Any
    file_example: dict
    glossary: dict

    model_name: str = GEMINI_MODEL
    cache_display_name: str = "few_shot_example"
    cache_ttl: timedelta = timedelta(minutes=5)

def process_video(
    video_file: str,
    config: ProcessingConfig,
    use_cache: bool = True
) -> Tuple[str, str]:
    """Process video with or without caching.
    
    Parameters
    ----------
    video_file : str
        Path to the video file
    config : ProcessingConfig
        Processing configuration
    use_cache : bool, optional
        Whether to use caching, defaults to True
    
    Returns
    -------
    Tuple[str, str]
        (markdown_output, original_filename)
    """
    try:
        processed_video = upload_video_and_wait(video_file)
        if use_cache:
            return _process_with_cache(processed_video, config, video_file)
        return _process_without_cache(processed_video, config, video_file)
    except Exception as e:
        return _handle_processing_error(e, video_file)

def _create_cache(config: ProcessingConfig) -> Any:
    """Create cache with model contents.
    
    Parameters
    ----------
    config : ProcessingConfig
        Processing configuration
    
    Returns
    -------
    Any
        CachedContent object
    """
    return caching.CachedContent.create(
        model=config.model_name,
        display_name=config.cache_display_name,
        contents=[
            config.prompts[0],
            config.video_example,
            config.prompts[1],
            {'mime_type': 'text/md', 'data': config.file_example},
            config.prompts[2],
            {'mime_type': 'text/md', 'data': config.glossary},
            config.prompts[3],
            config.prompts[4]
        ],
        ttl=config.cache_ttl,
    )

def _get_model_inputs(processed_video: Any, config: ProcessingConfig) -> List[Any]:
    """Get inputs for model processing.
    
    Parameters
    ----------
    processed_video : Any
        Processed video file
    config : ProcessingConfig
        Processing configuration
    
    Returns
    -------
    List[Any]
        List of model inputs
    """
    return [
        config.prompts[0],
        config.video_example,
        config.prompts[1],
        {'mime_type': 'text/md', 'data': config.file_example},
        config.prompts[2],
        {'mime_type': 'text/md', 'data': config.glossary},
        config.prompts[3],
        config.prompts[4],
        processed_video,
        config.prompts[5]
    ]

def _generate_response(
    model: Any,
    inputs: List[Any],
    timeout: Optional[int] = None,
    video_file: str = None
) -> Tuple[str, str]:
    """Generate response from model.
    
    Parameters
    ----------
    model : Any
        Generative model instance
    inputs : List[Any]
        Model inputs
    timeout : Optional[int]
        Request timeout in seconds
    
    Returns
    -------
    Tuple[str, str]
        (markdown_output, original_filename)
    """
    request_options = {"timeout": timeout} if timeout else None
    response = model.generate_content(
        inputs,
        request_options=request_options
    )
    print(response.usage_metadata)

    # Extract filename from the video path if provided
    original_filename = Path(video_file).stem if video_file else "protocol"

    return response.text, original_filename

def _process_with_cache(
    processed_video: Any,
    config: ProcessingConfig,
    video_file: str
) -> Tuple[str, str]:
    """Handle cached processing.
    
    Parameters
    ----------
    processed_video : Any
        Processed video file
    config : ProcessingConfig
        Processing configuration
    
    Returns
    -------
    Tuple[str, str]
        (markdown_output, original_filename)
    """
    cache = _create_cache(config)
    model = genai.GenerativeModel.from_cached_content(cached_content=cache)
    return _generate_response(model, [processed_video, config.prompts[5]], video_file=video_file)

def _process_without_cache(
    processed_video: Any,
    config: ProcessingConfig,
    video_file: str
) -> Tuple[str, str]:
    """Handle non-cached processing.
    
    Parameters
    ----------
    processed_video : Any
        Processed video file
    config : ProcessingConfig
        Processing configuration
    
    Returns
    -------
    Tuple[str, str]
        (markdown_output, original_filename)
    """
    model = genai.GenerativeModel(model_name=config.model_name)
    inputs = _get_model_inputs(processed_video, config)
    return _generate_response(model, inputs, timeout=DEFAULT_TIMEOUT, video_file=video_file)

def _handle_processing_error(error: Exception, video_file: str) -> Tuple[str, str]:
    """Handle processing errors.
    
    Parameters
    ----------
    error : Exception
        The caught exception
    video_file : str
        Original video file path
    
    Returns
    -------
    Tuple[str, str]
        Error message and original filename
    """
    markdown_output = f"**Error:** An error occurred during processing: {str(error)}"
    original_filename = Path(video_file).stem
    return markdown_output, original_filename


def generate_markdown_for_download(
    text: str,
    original_filename: str,
    temp_dir: Optional[str] = None
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
    temp_dir : str, optional
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
        # Input validation
        if not text or not original_filename:
            raise ValueError("Text and original_filename cannot be empty")
            
        # Clean filename and ensure .md extension
        clean_filename = Path(original_filename).stem
        markdown_filename = f"{clean_filename}.md"
        
        # Get temporary directory
        temp_path = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        if not temp_path.exists():
            temp_path.mkdir(parents=True, exist_ok=True)
            
        # Create full file path
        file_path = temp_path / markdown_filename
        
        # Write content with proper encoding
        file_path.write_text(text, encoding='utf-8')
        
        print(f"Created markdown file: {file_path}")
        return str(file_path)
        
    except OSError as e:
        print(f"Error creating markdown file: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise