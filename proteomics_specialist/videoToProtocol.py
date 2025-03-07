import os

def upload_video_to_gcs(path, bucket, subfolder_in_bucket=None, custom_blob_name=None):
    """
    Upload a video file to Google Cloud Storage and return its URI.
    Uses the original filename as the blob name by default.
    
    Args:
        path (str): Local path to the file
        bucket: GCS bucket object to upload to
        subfolder_in_bucket (str, optional): Optional subfolder path in the bucket (e.g., "knowledge")
        custom_blob_name (str, optional): Override the default blob name
    
    Returns:
        str: Cloud Storage URI for the uploaded video
    """
    # Extract filename from path if custom_blob_name is not provided
    if custom_blob_name is None:
        filename = os.path.basename(path)
    else:
        filename = custom_blob_name

    if subfolder_in_bucket:
        blob_name = os.path.join(subfolder_in_bucket, filename)
    else:
        blob_name = filename
    
    # Upload the video to Cloud Storage
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path)
    
    # Get and return the Cloud Storage URI
    uri = f"gs://{bucket.name}/{blob_name}"
    print(f"Uploaded to: {uri}")
    
    return uri


