"""Functions for the documentation assistant that converts media to Nature-style protocols using Gemini APIs."""

from __future__ import annotations

import datetime
import logging
import os
from collections import defaultdict
from pathlib import Path

from vertexai.generative_models import GenerationConfig, GenerativeModel, Part
from vertexai.preview import caching

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def upload_file_to_gcs(
    path: str,
    bucket: str,
    subfolder_in_bucket: str | None = None,
    custom_blob_name: str | None = None,
) -> str:
    """Upload a file to Google Cloud Storage and return its URI.

    Uses the original filename as the blob name by default.

    Parameters
    ----------
    path : str
        Local path to the file
    bucket : str
        GCS bucket object to upload to
    subfolder_in_bucket : str, optional
        Optional subfolder path in the bucket (e.g., "knowledge")
    custom_blob_name : str, optional
        Override the default blob name

    Returns
    -------
    str
        Cloud Storage URI for the uploaded file

    """
    path_obj = Path(path)
    filename = path_obj.name if custom_blob_name is None else custom_blob_name

    blob_name = f"{subfolder_in_bucket}/{filename}" if subfolder_in_bucket else filename

    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path)

    return f"gs://{bucket.name}/{blob_name}"


def create_cached_content(
    knowledge_uris: list[str],
    model_id: str,
) -> list[Part]:
    """Create cached content from knowledge URIs.

    Parameters
    ----------
    knowledge_uris : list[str]
        List of URIs pointing to knowledge files
    model_id : str
        ID of the model to use

    Returns
    -------
    list[Part]
        List of Part objects created from the knowledge URIs

    """
    contents = []
    file_counts = defaultdict(int)

    for file_path in knowledge_uris:
        path_obj = Path(file_path)
        file_ext = path_obj.suffix.lower()

        if file_ext in MIME_TYPES:
            mime_type = MIME_TYPES[file_ext]
            try:
                contents.append(Part.from_uri(file_path, mime_type=mime_type))
                file_counts[file_ext] += 1
            except (OSError, ValueError):
                logger.exception(f"Error creating Part from {file_path}")
        else:
            logger.warning(f"Unsupported file extension: {file_ext}")

    logger.info(f"Total files processed: {len(contents)}")
    for ext, count in file_counts.items():
        logger.info(f"  {ext[1:].upper()}: {count}")

    if contents:
        cached_content = caching.CachedContent.create(
            model_name=model_id,
            contents=contents,
            ttl=datetime.timedelta(minutes=60),
        )
        logger.info("Cached content created successfully!")
        return cached_content

    logger.warning("No matching files found. Cached content not created.")
    return None


def collect_knowledge_uris(
    folder_path: str, bucket: any, subfolder_in_bucket: str
) -> list[str]:
    """Create a list of GCS URIs from files in a folder.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing knowledge files
    bucket : object
        GCS bucket object for uploading the files
    subfolder_in_bucket : str
        Subfolder in the bucket where files should be uploaded

    Returns
    -------
    list[str]
        List of URIs pointing to uploaded knowledge files

    """
    knowledge_uris = []
    supported_extensions = (".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".pdf")

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_extensions):
            path = Path(folder_path) / filename
            try:
                file_uri = upload_file_to_gcs(path, bucket, subfolder_in_bucket)
                knowledge_uris.append(file_uri)
            except OSError:
                logging.exception(f"Error processing {filename}")

    return knowledge_uris


def generate_content_from_model(
    inputs: str | list,
    model_name: str,
    temperature: float,
) -> tuple:
    """Generate content using Google's Generative AI model.

    This function sends inputs to a specified Gemini model and returns the
    generated response along with usage metadata.

    Parameters
    ----------
    inputs : str, list
        The inputs to send to the model as str or list. The list can include text (str), images (Part), or videos (Part).
    model_name : str, default="gemini-2.5-pro-preview-03-25"
        Name of the generative model to use.
    temperature : float, default=0.9
        Controls the randomness of the output. Higher values (closer to 1.0)
        make output more random, lower values make it more deterministic.

    Returns
    -------
    tuple[str, any]
        A tuple containing (response_text, usage_metadata)

    Raises
    ------
    ValueError
        If the model fails to generate content.

    """
    try:
        model = GenerativeModel(model_name)

        generation_config = GenerationConfig(
            temperature=temperature,
            # Uncomment if using single audio/video input
            # audio_timestamp=True
        )

        response = model.generate_content(inputs, generation_config=generation_config)
        lab_notes = response.text
        usage_metadata = response.usage_metadata

    except Exception as e:
        logger.exception("Error during content generation")
        raise ValueError(f"Failed to generate content: {e!s}") from None

    return lab_notes, usage_metadata
