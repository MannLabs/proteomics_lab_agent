"""Functions for the documentation assistant that converts media to Nature-style protocols using Gemini APIs."""

from __future__ import annotations

from pathlib import Path


def upload_video_to_gcs(
    path: str,
    bucket: str,
    subfolder_in_bucket: str | None = None,
    custom_blob_name: str | None = None,
) -> str:
    """Upload a video file to Google Cloud Storage and return its URI.

    Uses the original filename as the blob name by default.

    Args:
        path (str): Local path to the file
        bucket: GCS bucket object to upload to
        subfolder_in_bucket (str, optional): Optional subfolder path in the bucket (e.g., "knowledge")
        custom_blob_name (str, optional): Override the default blob name

    Returns:
        str: Cloud Storage URI for the uploaded video

    """
    path_obj = Path(path)
    filename = path_obj.name if custom_blob_name is None else custom_blob_name

    blob_name = f"{subfolder_in_bucket}/{filename}" if subfolder_in_bucket else filename

    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path)

    return f"gs://{bucket.name}/{blob_name}"
