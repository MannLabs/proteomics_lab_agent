"""Unit tests for sub_agents.utils module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from proteomics_lab_agent.sub_agents.utils import (
    _get_gcs_file_paths,
    _get_local_file_paths,
    _process_file_paths,
    _process_single_file,
    extract_file_path_and_message,
    generate_part_from_path,
    generate_parts_from_folder,
    get_blob_name_from_gcs_path,
    upload_file_from_path_to_gcs,
)

# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


def test_extract_file_path_and_message_with_gcs_uri() -> None:
    """Test extraction of GCS URI from query string."""
    # given
    query = 'Analyse this video: "gs://ai-proteomics-advisor/input_video/test.mp4".'

    # when
    file_path, filename, remaining_message = extract_file_path_and_message(query)

    # then
    assert file_path == "gs://ai-proteomics-advisor/input_video/test.mp4"
    assert filename == "test.mp4"
    assert remaining_message == 'Analyse this video: "".'


def test_extract_file_path_and_message_with_quoted_local_path() -> None:
    """Test extraction of quoted local file path."""
    # given
    query = '"/Users/patriciaskowronek/Downloads/ultra_short.mp4".'

    # when
    file_path, filename, remaining_message = extract_file_path_and_message(query)

    # then
    assert file_path == "/Users/patriciaskowronek/Downloads/ultra_short.mp4"
    assert filename == "ultra_short.mp4"
    assert remaining_message == "."


def test_extract_file_path_and_message_with_unquoted_path() -> None:
    """Test extraction of unquoted file path with path separators."""
    # given
    query = "Video path: /Users/test/video.mp4. Analyze the video."

    # when
    file_path, filename, remaining_message = extract_file_path_and_message(query)

    # then
    assert file_path == "/Users/test/video.mp4"
    assert filename == "video.mp4"
    assert remaining_message == "Video path: <removed_file_path>. Analyze the video."


def test_extract_file_path_and_message_no_file_path() -> None:
    """Test that query without file path returns None."""
    # given
    query = "This is a simple query without any file path"

    # when
    file_path, filename, remaining_message = extract_file_path_and_message(query)

    # then
    assert file_path is None
    assert filename is None
    assert remaining_message == "This is a simple query without any file path"


def test_get_blob_name_from_gcs_path_with_nested_path() -> None:
    """Test extraction of blob name from GCS path with nested folders."""
    # given
    gcs_path = "gs://my-bucket/folder/subfolder/file.mp4"

    # when
    blob_name = get_blob_name_from_gcs_path(gcs_path)

    # then
    assert blob_name == "folder/subfolder/file.mp4"


def test_get_blob_name_from_gcs_path_with_single_file() -> None:
    """Test extraction of blob name from GCS path with file at root."""
    # given
    gcs_path = "gs://my-bucket/file.mp4"

    # when
    blob_name = get_blob_name_from_gcs_path(gcs_path)

    # then
    assert blob_name == "file.mp4"


def test_upload_file_from_path_to_gcs_with_video_metadata() -> None:
    """Test successful file upload with video metadata extraction."""
    # given
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_bucket.blob.return_value = mock_blob
    mock_bucket.name = "test-bucket"

    probe_result = {"format": {"duration": "120.5", "size": "1048576"}}

    with patch(
        "proteomics_lab_agent.sub_agents.utils.ffmpeg.probe", return_value=probe_result
    ):
        # when
        path_obj, gcs_uri, filename, blob = upload_file_from_path_to_gcs(
            "/path/to/video.mp4", mock_bucket
        )

        # then
        assert path_obj == Path("/path/to/video.mp4")
        assert gcs_uri == "gs://test-bucket/video.mp4"
        assert filename == "video.mp4"
        assert blob == mock_blob
        assert blob.metadata == {
            "duration": "120.5",
            "file_size": "1048576",
            "input_type": "video",
        }
        mock_blob.upload_from_filename.assert_called_once_with("/path/to/video.mp4")


def test_upload_file_from_path_to_gcs_with_subfolder() -> None:
    """Test file upload to subfolder in bucket."""
    # given
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_bucket.blob.return_value = mock_blob
    mock_bucket.name = "test-bucket"

    with patch("proteomics_lab_agent.sub_agents.utils.ffmpeg.probe") as mock_probe:
        mock_probe.side_effect = OSError("Not a video")

        # when
        path_obj, gcs_uri, filename, blob = upload_file_from_path_to_gcs(
            "/path/to/document.pdf", mock_bucket, subfolder_in_bucket="documents"
        )

        # then
        assert gcs_uri == "gs://test-bucket/documents/document.pdf"
        assert filename == "document.pdf"
        mock_bucket.blob.assert_called_once_with("documents/document.pdf")


def test_generate_part_from_path_with_local_file() -> None:
    """Test generating Part from local file path."""
    # given
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_blob.metadata = {"duration": "120", "file_size": "1024"}
    mock_bucket.blob.return_value = mock_blob
    mock_bucket.name = "test-bucket"

    probe_result = {"format": {"duration": "120", "size": "1024"}}

    with (
        patch(
            "proteomics_lab_agent.sub_agents.utils.ffmpeg.probe",
            return_value=probe_result,
        ),
        patch("proteomics_lab_agent.sub_agents.utils.types.Part.from_uri") as mock_part,
    ):
        mock_part_obj = Mock()
        mock_part.return_value = mock_part_obj

        # when
        result = generate_part_from_path("/path/to/video.mp4", mock_bucket)

        # then
        assert result["local_path"] == Path("/path/to/video.mp4")
        assert result["gcs_uri"] == "gs://test-bucket/video.mp4"
        assert result["filename"] == "video.mp4"
        assert result["mime_type"] == "video/mp4"
        assert result["part"] == mock_part_obj
        assert result["metadata"] == {
            "duration": "120.0",
            "file_size": "1024",
            "input_type": "video",
        }


def test_generate_part_from_path_with_gcs_uri() -> None:
    """Test generating Part from existing GCS URI."""
    # given
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_blob.metadata = {}
    mock_bucket.blob.return_value = mock_blob

    with patch(
        "proteomics_lab_agent.sub_agents.utils.types.Part.from_uri"
    ) as mock_part:
        mock_part_obj = Mock()
        mock_part.return_value = mock_part_obj

        # when
        result = generate_part_from_path(
            "gs://test-bucket/folder/video.mp4", mock_bucket
        )

        # then
        assert result["gcs_uri"] == "gs://test-bucket/folder/video.mp4"
        assert result["filename"] == "video.mp4"
        assert result["mime_type"] == "video/mp4"
        assert mock_bucket.blob.return_value.reload.called


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_extract_file_path_and_message_with_multiple_extensions() -> None:
    """Test extraction works with various supported file extensions."""
    # given
    test_cases = [
        ("path/file.avi", "file.avi"),
        ("path/file.mov", "file.mov"),
        ("path/file.mkv", "file.mkv"),
        ("path/file.mp3", "file.mp3"),
        ("path/file.wav", "file.wav"),
        ("path/file.jpg", "file.jpg"),
        ("path/file.png", "file.png"),
        ("path/file.pdf", "file.pdf"),
        ("path/file.txt", "file.txt"),
        ("path/file.csv", "file.csv"),
    ]

    for path, expected_filename in test_cases:
        query = f'File: "{path}"'

        # when
        file_path, filename, _ = extract_file_path_and_message(query)

        # then
        assert file_path == path
        assert filename == expected_filename


def test_extract_file_path_and_message_with_single_quotes() -> None:
    """Test extraction with single-quoted paths."""
    # given
    query = "Analyze '/path/to/video.mp4' please"

    # when
    file_path, filename, remaining_message = extract_file_path_and_message(query)

    # then
    assert file_path == "/path/to/video.mp4"
    assert filename == "video.mp4"
    assert remaining_message == "Analyze  please"


def test_get_blob_name_from_gcs_path_with_no_path() -> None:
    """Test blob name extraction when path has only bucket."""
    # given
    gcs_path = "gs://my-bucket/"

    # when
    blob_name = get_blob_name_from_gcs_path(gcs_path)

    # then
    assert blob_name == ""


def test_upload_file_from_path_to_gcs_with_custom_blob_name() -> None:
    """Test file upload with custom blob name."""
    # given
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_bucket.blob.return_value = mock_blob
    mock_bucket.name = "test-bucket"

    with patch("proteomics_lab_agent.sub_agents.utils.ffmpeg.probe") as mock_probe:
        mock_probe.side_effect = OSError()

        # when
        _, gcs_uri, filename, _ = upload_file_from_path_to_gcs(
            "/path/to/video.mp4", mock_bucket, custom_blob_name="custom_name.mp4"
        )

        # then
        assert filename == "custom_name.mp4"
        assert gcs_uri == "gs://test-bucket/custom_name.mp4"
        mock_bucket.blob.assert_called_once_with("custom_name.mp4")


def test_upload_file_from_path_to_gcs_without_metadata() -> None:
    """Test file upload when ffmpeg metadata extraction fails."""
    # given
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_bucket.blob.return_value = mock_blob
    mock_bucket.name = "test-bucket"

    with patch("proteomics_lab_agent.sub_agents.utils.ffmpeg.probe") as mock_probe:
        mock_probe.side_effect = OSError("ffmpeg error")

        # when
        path_obj, gcs_uri, filename, blob = upload_file_from_path_to_gcs(
            "/path/to/document.pdf", mock_bucket
        )

        # then
        assert gcs_uri == "gs://test-bucket/document.pdf"
        mock_blob.upload_from_filename.assert_called_once_with("/path/to/document.pdf")


def test_get_local_file_paths_with_extension_filter() -> None:
    """Test getting local file paths with extension filter."""
    # given
    with (
        patch("proteomics_lab_agent.sub_agents.utils.os.walk") as mock_walk,
        patch("proteomics_lab_agent.sub_agents.utils.Path") as mock_path_class,
    ):
        call_count = [0]

        def path_side_effect(p):  # noqa: ANN001, ANN202
            call_count[0] += 1
            # First two calls are for existence and directory checks
            if call_count[0] <= 2 and p == "/test":
                mock = Mock()
                mock.exists.return_value = True
                mock.is_dir.return_value = True
                return mock
            # All other calls use real Path
            return Path(p)

        mock_path_class.side_effect = path_side_effect

        mock_walk.return_value = [("/test", [], ["video.mp4", "doc.pdf", "image.jpg"])]

        # when
        result = _get_local_file_paths("/test", [".mp4", ".jpg"])

        # then
        assert len(result) == 2
        assert "/test/video.mp4" in result
        assert "/test/image.jpg" in result


def test_get_local_file_paths_without_filter() -> None:
    """Test getting all local file paths without filter."""
    # given
    with (
        patch("proteomics_lab_agent.sub_agents.utils.os.walk") as mock_walk,
        patch("proteomics_lab_agent.sub_agents.utils.Path") as mock_path_class,
    ):
        call_count = [0]

        def path_side_effect(p):  # noqa: ANN001, ANN202
            call_count[0] += 1
            if call_count[0] <= 2 and p == "/test":
                mock = Mock()
                mock.exists.return_value = True
                mock.is_dir.return_value = True
                return mock
            return Path(p)

        mock_path_class.side_effect = path_side_effect

        mock_walk.return_value = [("/test", [], ["video.mp4", "doc.pdf"])]

        # when
        result = _get_local_file_paths("/test", None)

        # then
        assert len(result) == 2
        assert "/test/video.mp4" in result
        assert "/test/doc.pdf" in result


def test_get_gcs_file_paths_with_extension_filter() -> None:
    """Test getting GCS file paths with extension filter."""
    # given
    mock_blob1 = Mock()
    mock_blob1.name = "folder/video.mp4"
    mock_blob2 = Mock()
    mock_blob2.name = "folder/doc.pdf"
    mock_blob3 = Mock()
    mock_blob3.name = "folder/image.jpg"

    with patch("google.cloud.storage.Client") as mock_client:
        mock_bucket = Mock()
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]
        mock_client.return_value.bucket.return_value = mock_bucket

        # when
        result = _get_gcs_file_paths("gs://test-bucket/folder", [".mp4", ".jpg"])

        # then
        assert len(result) == 2
        assert "gs://test-bucket/folder/video.mp4" in result
        assert "gs://test-bucket/folder/image.jpg" in result


def test_get_gcs_file_paths_skips_folders() -> None:
    """Test that GCS file path extraction skips folder blobs."""
    # given
    mock_blob1 = Mock()
    mock_blob1.name = "folder/"
    mock_blob2 = Mock()
    mock_blob2.name = "folder/video.mp4"

    with patch("google.cloud.storage.Client") as mock_client:
        mock_bucket = Mock()
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_client.return_value.bucket.return_value = mock_bucket

        # when
        result = _get_gcs_file_paths("gs://test-bucket/folder", None)

        # then
        assert len(result) == 1
        assert "gs://test-bucket/folder/video.mp4" in result


def test_process_single_file_returns_result_on_success() -> None:
    """Test that _process_single_file returns result for valid file."""
    # given
    mock_bucket = Mock()

    with patch(
        "proteomics_lab_agent.sub_agents.utils.generate_part_from_path"
    ) as mock_generate:
        expected_result = {"part": "mock_part", "filename": "test.mp4"}
        mock_generate.return_value = expected_result

        # when
        result = _process_single_file("/path/to/test.mp4", mock_bucket, "subfolder")

        # then
        assert result == expected_result
        mock_generate.assert_called_once_with(
            "/path/to/test.mp4", mock_bucket, "subfolder"
        )


def test_process_single_file_returns_none_on_error() -> None:
    """Test that _process_single_file returns None when processing fails."""
    # given
    mock_bucket = Mock()

    with patch(
        "proteomics_lab_agent.sub_agents.utils.generate_part_from_path"
    ) as mock_generate:
        mock_generate.side_effect = OSError("File not found")

        # when
        result = _process_single_file("/path/to/nonexistent.mp4", mock_bucket, None)

        # then
        assert result is None


def test_process_file_paths_returns_parts_and_summary() -> None:
    """Test that _process_file_paths processes multiple files and returns summary."""
    # given
    mock_bucket = Mock()
    file_paths = ["/path/file1.mp4", "/path/file2.mp4"]

    mock_part1 = Mock()
    mock_part2 = Mock()

    with patch(
        "proteomics_lab_agent.sub_agents.utils.generate_part_from_path"
    ) as mock_generate:
        mock_generate.side_effect = [
            {"part": mock_part1, "filename": "file1.mp4", "mime_type": "video/mp4"},
            {"part": mock_part2, "filename": "file2.mp4", "mime_type": "video/mp4"},
        ]

        # when
        result = _process_file_paths(file_paths, "/path", mock_bucket, None)

        # then
        assert len(result["parts"]) == 2
        assert result["parts"][0] == mock_part1
        assert result["parts"][1] == mock_part2
        assert len(result["files_info"]) == 2
        assert result["summary"]["total_files"] == 2
        assert result["summary"]["successful_uploads"] == 2
        assert result["summary"]["folder_path"] == "/path"


def test_generate_parts_from_folder_with_local_folder() -> None:
    """Test processing local folder with multiple files."""
    # given
    mock_bucket = Mock()

    with (
        patch(
            "proteomics_lab_agent.sub_agents.utils._get_local_file_paths"
        ) as mock_get_paths,
        patch(
            "proteomics_lab_agent.sub_agents.utils._process_file_paths"
        ) as mock_process,
    ):
        mock_get_paths.return_value = ["/folder/file1.mp4", "/folder/file2.mp4"]
        expected_result = {
            "parts": ["part1", "part2"],
            "files_info": [{"filename": "file1.mp4"}, {"filename": "file2.mp4"}],
            "summary": {"total_files": 2},
        }
        mock_process.return_value = expected_result

        # when
        result = generate_parts_from_folder(
            "/folder", mock_bucket, "subfolder", [".mp4"]
        )

        # then
        assert result == expected_result
        mock_get_paths.assert_called_once_with("/folder", [".mp4"])
        mock_process.assert_called_once_with(
            ["/folder/file1.mp4", "/folder/file2.mp4"],
            "/folder",
            mock_bucket,
            "subfolder",
        )


def test_generate_parts_from_folder_with_gcs_folder() -> None:
    """Test processing GCS folder with multiple files."""
    # given
    mock_bucket = Mock()

    with (
        patch(
            "proteomics_lab_agent.sub_agents.utils._get_gcs_file_paths"
        ) as mock_get_paths,
        patch(
            "proteomics_lab_agent.sub_agents.utils._process_file_paths"
        ) as mock_process,
    ):
        mock_get_paths.return_value = ["gs://bucket/file1.mp4", "gs://bucket/file2.mp4"]
        expected_result = {
            "parts": ["part1", "part2"],
            "files_info": [{"filename": "file1.mp4"}, {"filename": "file2.mp4"}],
            "summary": {"total_files": 2},
        }
        mock_process.return_value = expected_result

        # when
        result = generate_parts_from_folder(
            "gs://bucket/folder", mock_bucket, None, [".mp4"]
        )

        # then
        assert result == expected_result
        mock_get_paths.assert_called_once_with("gs://bucket/folder", [".mp4"])


# ============================================================================
# ERROR CASE TESTS
# ============================================================================


def test_get_blob_name_from_gcs_path_raises_error_for_invalid_path() -> None:
    """Test that invalid GCS path raises ValueError."""
    # given
    invalid_path = "/local/path/to/file.mp4"

    # when/then
    with pytest.raises(ValueError, match="Invalid GCS path"):
        get_blob_name_from_gcs_path(invalid_path)


def test_get_local_file_paths_raises_error_for_nonexistent_folder() -> None:
    """Test that nonexistent folder raises ValueError."""
    # given
    nonexistent_path = "/path/that/does/not/exist"

    # when/then
    with pytest.raises(ValueError, match="Folder path does not exist"):
        _get_local_file_paths(nonexistent_path, None)


def test_get_local_file_paths_raises_error_for_non_directory() -> None:
    """Test that file path instead of directory raises ValueError."""
    # given
    with patch("proteomics_lab_agent.sub_agents.utils.Path") as mock_path:
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = False
        mock_path.return_value = mock_path_instance

        # when/then
        with pytest.raises(ValueError, match="Path is not a directory"):
            _get_local_file_paths("/path/to/file.txt", None)


# ============================================================================
# UNCOVERED TEST CASES
# ============================================================================
# Review these and decide which to implement:
#
# test_generate_parts_from_folder_handles_empty_folder
# """Test folder processing with no matching files."""
# value: 6/10 (edge case handling)
# approach: create new test with _process_file_paths returning empty results
#
# test_extract_file_path_and_message_with_special_characters
# """Test path extraction with spaces, unicode, etc in file paths."""
# value: 5/10 (edge case, may not be common)
# approach: parametrize test with special character paths
#
# test_upload_file_from_path_to_gcs_handles_partial_metadata
# """Test when ffmpeg returns incomplete metadata (KeyError/ValueError)."""
# value: 6/10 (error resilience)
# approach: mock ffmpeg.probe to raise KeyError/ValueError and verify graceful handling
#
# test_generate_part_from_path_handles_missing_mime_type
# """Test when mimetypes.guess_type returns None."""
# value: 5/10 (edge case)
# approach: patch mimetypes.guess_type to return (None, None)
#
# test_process_file_paths_with_partial_failures
# """Test when some files fail to process but others succeed."""
# value: 7/10 (realistic scenario)
# approach: mock _process_single_file to return None for some files
#
# test_extract_file_path_and_message_case_insensitive_extensions
# """Test that file extension matching is case-insensitive."""
# value: 4/10 (already shown to work in test_extract_file_path_and_message_with_multiple_extensions)
# approach: add .MP4, .PDF cases to parametrized test
#
# test_get_gcs_file_paths_with_empty_bucket
# """Test GCS path extraction from empty bucket or folder."""
# value: 5/10 (edge case)
# approach: mock list_blobs to return empty list
