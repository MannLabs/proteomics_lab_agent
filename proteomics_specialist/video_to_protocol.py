"""Functions for the documentation assistant that converts media to Nature-style protocols using Gemini APIs."""

from __future__ import annotations

from pathlib import Path
import os
from collections import defaultdict
import datetime

import vertexai
from vertexai.generative_models import Part
from vertexai.preview import caching


MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


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


def create_cached_content(
    knowledge_uris: list[str],
    model_id: str,
) -> list[Part]:
    """Create cached content from knowledge URIs.

    Args:
        knowledge_uris: list of URIs pointing to knowledge files
        bucket_name: Name of the GCS bucket
        subfolder_in_bucket: Subfolder path in the bucket
        model_id: ID of the model to use

    Returns:
        list of Part objects created from the knowledge URIs

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
            except (OSError, ValueError) as e:
                print(f"Error creating Part from {file_path}: {e}")
        else:
            print(f"Unsupported file extension: {file_ext}")

    print(f"Total files processed: {len(contents)}")
    for ext, count in file_counts.items():
        print(f"  {ext[1:].upper()}: {count}")

    if contents:
        cached_content = caching.CachedContent.create(
            model_name=model_id,
            contents=contents,
            ttl=datetime.timedelta(minutes=60),
        )
        print("Cached content created successfully!")
        return cached_content
    print("No matching files found. Cached content not created.")
    return None
