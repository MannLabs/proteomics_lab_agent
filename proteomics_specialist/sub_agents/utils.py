"""Helper functions for subagents."""

from __future__ import annotations

import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg
from google.genai import types

if TYPE_CHECKING:
    from google.cloud.storage import Blob, Bucket

logger = logging.getLogger(__name__)


def extract_file_path_and_message(query: str) -> tuple[str | None, str | None, str]:
    """Extract file path and remaining message from query.

    Parameters
    ----------
    query : str
        Input string that may contain a file path.

    Returns
    -------
    tuple[str | None, str | None, str]
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

    return None, None, query.strip()


def upload_file_from_path_to_gcs(
    path: str,
    bucket: Bucket,
    subfolder_in_bucket: str | None = None,
    custom_blob_name: str | None = None,
) -> tuple[Path, str, str, Blob]:
    """Upload a file to Google Cloud Storage and return its URI.

    Uses the original filename as the blob name by default.

    Parameters
    ----------
    path : str
        Local path to the file
    bucket : storage.Bucket
        GCS bucket object for upload
    subfolder_in_bucket : str, optional
        Optional subfolder path in the bucket (e.g., "video_files")
    custom_blob_name : str, optional
        Override the default blob name
    add_video_metadata : bool, optional
        If True, attempt to extract and add video metadata. Default is True.

    Returns
    -------
    tuple[Path, str, str, Blob]
        Tuple containing (path_obj, gcs_uri, filename, blob)

    """
    path_obj = Path(path)
    filename = path_obj.name if custom_blob_name is None else custom_blob_name
    blob_name = f"{subfolder_in_bucket}/{filename}" if subfolder_in_bucket else filename
    blob = bucket.blob(blob_name)

    try:
        probe = ffmpeg.probe(path)
        duration = float(probe["format"]["duration"])
        file_size = int(probe["format"]["size"])

        custom_metadata = {
            "duration": str(duration),
            "file_size": str(file_size),
            "input_type": "video",
        }
        blob.metadata = custom_metadata
        logging.info(f"custom_metadata: {custom_metadata}")
    except ffmpeg.Error as e:
        logging.warning(f"Could not extract video metadata via ffmpeg: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logging.warning(f"Could not parse video metadata: {e}")
    except OSError as e:
        logging.warning(f"Could not access file for metadata extraction: {e}")

    blob.upload_from_filename(path)
    return path_obj, f"gs://{bucket.name}/{blob_name}", filename, blob


def get_blob_name_from_gcs_path(gcs_path: str) -> str:
    """Extract blob name from GCS path.

    Parameters
    ----------
    gcs_path : str
        GCS path (gs://bucket/path/to/file).

    Returns
    -------
    str
        Blob name (path/to/file).

    """
    if gcs_path.startswith("gs://"):
        path_without_prefix = gcs_path[5:]
        parts = path_without_prefix.split("/", 1)
        if len(parts) > 1:
            return parts[1]
        return ""
    raise ValueError(f"Invalid GCS path: {gcs_path}")


def generate_part_from_path(
    path: str,
    bucket: Bucket,
    subfolder_in_bucket: str | None = None,
) -> dict[str, str | Any]:
    """Generate a Part (google genai object) from a file uploaded to GCS.

    Uploads a local file to Google Cloud Storage and creates a Part object
    with the file URI and MIME type for use with multimodal models.

    Parameters
    ----------
    path : str
        Local path to the file to upload
    bucket : storage.Bucket
        GCS bucket object for upload
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
        - metadata: Only if video: duration and file size

    """
    if path.startswith("gs://"):
        logging.info("Path is already a GCS URI, skipping upload: %s", path)

        path_obj = Path(path)
        filename = path_obj.name

        file_uri = path
        file_path = path
        blob_name = get_blob_name_from_gcs_path(file_path)
        blob = bucket.blob(blob_name)
        blob.reload()

    else:
        logging.info(f"Uploading local file to GCS: {path}")
        file_path, file_uri, filename, blob = upload_file_from_path_to_gcs(
            path, bucket, subfolder_in_bucket
        )

    mime_type, _ = mimetypes.guess_type(filename)

    file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
    logging.info(blob.metadata)
    return {
        "local_path": file_path,
        "gcs_uri": file_uri,
        "part": file_part,
        "filename": filename,
        "mime_type": mime_type,
        "metadata": blob.metadata or {},
    }


def generate_parts_from_folder(
    folder_path: str,
    bucket: Bucket,
    subfolder_in_bucket: str | None = None,
    file_extensions: list[str] | None = None,
) -> dict:
    """Process an entire folder (local or GCS) and generate parts for all files.

    Parameters
    ----------
    folder_path : str
        Path to the folder to process
    bucket : storage.Bucket
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
    if folder_path.startswith("gs://"):
        file_paths = _get_gcs_file_paths(folder_path, file_extensions)
    else:
        file_paths = _get_local_file_paths(folder_path, file_extensions)

    return _process_file_paths(file_paths, folder_path, bucket, subfolder_in_bucket)


def _get_gcs_file_paths(
    gcs_folder_path: str, file_extensions: list[str] | None
) -> list[str]:
    """Get list of GCS file URIs from a GCS folder."""
    from google.cloud import storage

    path_parts = gcs_folder_path[5:].split("/", 1)  # Remove gs://
    gcs_bucket_name = path_parts[0]
    folder_prefix = path_parts[1] if len(path_parts) > 1 else ""

    client = storage.Client()
    gcs_bucket = client.bucket(gcs_bucket_name)
    blobs = gcs_bucket.list_blobs(prefix=folder_prefix)

    file_paths = []
    for blob in blobs:
        if blob.name.endswith("/"):  # Skip folders
            continue

        if file_extensions:
            file_ext = Path(blob.name).suffix.lower()
            if file_ext not in file_extensions:
                continue

        file_paths.append(f"gs://{gcs_bucket_name}/{blob.name}")

    return file_paths


def _get_local_file_paths(
    folder_path: str, file_extensions: list[str] | None
) -> list[str]:
    """Get list of local file paths from a local folder."""
    if not Path(folder_path).exists():
        raise ValueError(f"Folder path does not exist: {folder_path}")
    if not Path(folder_path).is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    file_paths = []
    for root, _dirs, files in os.walk(folder_path):
        for file in files:
            file_path = Path(root) / file

            if file_extensions:
                file_ext = file_path.suffix.lower()
                if file_ext not in file_extensions:
                    continue

            file_paths.append(str(file_path))

    return file_paths


def _process_single_file(
    file_path: str, bucket: str, subfolder_in_bucket: str | None
) -> dict | None:
    """Process a single file and return result or None if failed."""
    try:
        return generate_part_from_path(file_path, bucket, subfolder_in_bucket)
    except (OSError, ValueError, TypeError) as e:
        logger.warning("Failed to process %s: %s", file_path, e)
        return None


def _process_file_paths(
    file_paths: list[str],
    original_folder_path: str,
    bucket: Bucket,
    subfolder_in_bucket: str | None,
) -> dict:
    """Process a list of file paths and generate parts."""
    parts_list = []
    files_info = []

    for file_path in file_paths:
        file_result = _process_single_file(file_path, bucket, subfolder_in_bucket)
        if file_result is not None:
            parts_list.append(file_result["part"])
            files_info.append(file_result)

    summary = {
        "folder_path": original_folder_path,
        "total_files": len(files_info),
        "successful_uploads": len(parts_list),
        "file_types": {info["mime_type"] for info in files_info if info["mime_type"]},
    }

    return {
        "parts": parts_list,
        "files_info": files_info,
        "summary": summary,
    }
