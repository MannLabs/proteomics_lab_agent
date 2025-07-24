"""Helper functions for subagents."""

from __future__ import annotations

import logging
import mimetypes
import os
import re
from pathlib import Path

from google.genai import types

logger = logging.getLogger(__name__)

# import config


def get_required_env(var_name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value


def extract_file_path_and_message(query: str) -> tuple[str | None, str | None, str]:
    """Extract file path and remaining message from query.

    Parameters
    ----------
    query : str
        Input string that may contain a file path.

    Returns
    -------
    tuple
        Tuple of (file_path, filename, remaining_message).

    """
    # Pattern for GCS URIs (gs://)
    gcs_pattern = r"(gs://[^\s\'\"]+\.(mp4|avi|mov|mkv|mp3|wav|jpg|png|pdf|txt|csv))"
    match = re.search(gcs_pattern, query, re.IGNORECASE)
    if match:
        file_path = match.group(1)
        filename = Path(file_path).name
        remaining_message = query.replace(file_path, "").strip()
        return file_path, filename, remaining_message

    # Pattern for quoted file paths (single or double quotes)
    quoted_pattern = (
        r"""(['"])([^'"]*\.(mp4|avi|mov|mkv|mp3|wav|jpg|png|pdf|txt|csv))\1"""
    )
    match = re.search(quoted_pattern, query, re.IGNORECASE)

    if match:
        file_path = match.group(2)
        filename = Path(file_path).name
        remaining_message = re.sub(
            quoted_pattern, "", query, flags=re.IGNORECASE
        ).strip()
        return file_path, filename, remaining_message

    # Pattern for unquoted file paths (must contain path separators to avoid false matches)
    unquoted_pattern = (
        r"""([/\\][^\s'"]*\.(mp4|avi|mov|mkv|mp3|wav|jpg|png|pdf|txt|csv))"""
    )
    match = re.search(unquoted_pattern, query, re.IGNORECASE)

    if match:
        file_path = match.group(1)
        filename = Path(file_path).name
        remaining_message = query.replace(file_path, "").strip()
        return file_path, filename, remaining_message

    # No file found
    return None, None, query.strip()


def upload_file_from_path_to_gcs(
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
        Optional subfolder path in the bucket (e.g., "video_files")
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

    return path_obj, f"gs://{bucket.name}/{blob_name}", filename


def generate_part_from_path(
    path: str,
    bucket: str,
    subfolder_in_bucket: str | None = None,
) -> dict:
    """Generate a Part (google genai object) from a file uploaded to GCS.

    Uploads a local file to Google Cloud Storage and creates a Part object
    with the file URI and MIME type for use with multimodal models.

    Parameters
    ----------
    path : str
        Local path to the file to upload
    bucket : str
        GCS bucket name to upload to
    subfolder_in_bucket : str, optional
        Optional subfolder path in the bucket (e.g., "knowledge")

    Returns
    -------
    dict
        Dictionary containing:
        - local_path: Original local file path
        - gcs_uri: Cloud Storage URI for the uploaded file
        - part: Part object created from the file URI
        - filename: Name of the uploaded file
        - mime_type: MIME type of the file

    """
    if path.startswith("gs://"):
        logging.info(f"Path is already a GCS URI, skipping upload: {path}")

        path_obj = Path(path)
        filename = path_obj.name

        file_uri = path
        file_path = path

    else:
        # Upload local file to GCS
        logging.info(f"Uploading local file to GCS: {path}")
        file_path, file_uri, filename = upload_file_from_path_to_gcs(
            path, bucket, subfolder_in_bucket
        )

    mime_type, _ = mimetypes.guess_type(filename)

    file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
    return {
        "local_path": file_path,
        "gcs_uri": file_uri,
        "part": file_part,
        "filename": filename,
        "mime_type": mime_type,
    }


def generate_parts_from_folder(
    folder_path: str,
    bucket: str,
    subfolder_in_bucket: str | None = None,
    file_extensions: list[str] | None = None,
) -> dict:
    """Process an entire folder and generate parts for all files.

    Parameters
    ----------
    folder_path : str
        Path to the folder to process
    bucket : str
        GCS bucket name
    subfolder_in_bucket : str, optional
        Optional subfolder in the bucket
    file_extensions : list, optional
        Optional list of extensions to filter (e.g., ['.pdf', '.txt'])

    Returns
    -------
    dict
        Dictionary containing:
        - 'parts': List of types.Part objects ready for model input
        - 'files_info': List of file information dictionaries
        - 'summary': Summary statistics

    """
    if not Path(folder_path).exists():
        raise ValueError(f"Folder path does not exist: {folder_path}")

    if not Path(folder_path).is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    parts_list = []
    files_info = []

    for root, _dirs, files in os.walk(folder_path):
        for file in files:
            file_path = Path(root) / file

            if file_extensions:
                file_ext = file_path.suffix.lower()
                if file_ext not in file_extensions:
                    continue

            try:
                file_result = generate_part_from_path(
                    file_path, bucket, subfolder_in_bucket
                )

                parts_list.append(file_result["part"])
                files_info.append(file_result)

            except (OSError, ValueError, TypeError) as e:
                logger.warning("Failed to process %s: %s", file_path, e)
                continue

    summary = {
        "folder_path": folder_path,
        "total_files": len(files_info),
        "successful_uploads": len(parts_list),
        "file_types": {info["mime_type"] for info in files_info if info["mime_type"]},
    }

    return {
        "parts": parts_list,
        "files_info": files_info,
        "summary": summary,
    }

    # config.model
