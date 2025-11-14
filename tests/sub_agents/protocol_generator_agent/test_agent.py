"""Unit tests for protocol_generator_agent.agent module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from proteomics_lab_agent.sub_agents.protocol_generator_agent import agent

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_env_vars() -> dict[str, str]:
    """Provide mock environment variables for tests."""
    return {
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test-bucket/knowledge",
        "example_protocol1_path": "gs://test-bucket/protocol1.pdf",
        "example_video1_path": "gs://test-bucket/video1.mp4",
        "example_protocol2_path": "gs://test-bucket/protocol2.pdf",
        "example_video2_path": "gs://test-bucket/video2.mp4",
    }


# ============================================================================
# Tests for generate_protocols - Happy Path
# ============================================================================


def test_generate_protocols_returns_success_with_video_input(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols successfully processes video input."""
    # given
    query = "Video path: /path/to/video.mp4. Analyze this video."

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "# Protocol Title\n\n## Abstract\n\nTest protocol content."
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/video.mp4",
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }
    mock_example_parts = {
        "protocol1": {"part": types.Part.from_text(text="mock protocol1")},
        "video1": {"part": types.Part.from_text(text="mock video1")},
        "protocol2": {"part": types.Part.from_text(text="mock protocol2")},
        "video2": {"part": types.Part.from_text(text="mock video2")},
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            return_value=(MagicMock(), mock_bucket, mock_client),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message",
            return_value=("/path/to/video.mp4", "video.mp4", "Analyze this video."),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path",
            side_effect=[
                mock_example_parts["protocol1"],
                mock_example_parts["video1"],
                mock_example_parts["protocol2"],
                mock_example_parts["video2"],
                mock_video_part,
            ],
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "success",
        "local_video_path": "/path/to/video.mp4",
        "gcs_video_path": "gs://test-bucket/video.mp4",
        "video_name": "video.mp4",
        "remaining_message": "Video path: /path/to/video.mp4. Analyze this video.",
        "protocol": "# Protocol Title\n\n## Abstract\n\nTest protocol content.",
        "usage_metadata": {"input_tokens": 100, "output_tokens": 50},
        "protocol_generation_time": result["protocol_generation_time"],
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }


def test_generate_protocols_returns_success_with_text_input(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols successfully processes text input."""
    # given
    query = "Create a protocol for PCR amplification with specific primers."

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "# PCR Protocol\n\n## Abstract\n\nPCR amplification protocol."
    mock_response.usage_metadata = {"input_tokens": 50, "output_tokens": 30}
    mock_client.models.generate_content.return_value = mock_response

    mock_example_parts = {
        "protocol1": {"part": types.Part.from_text(text="mock protocol1")},
        "video1": {"part": types.Part.from_text(text="mock video1")},
        "protocol2": {"part": types.Part.from_text(text="mock protocol2")},
        "video2": {"part": types.Part.from_text(text="mock video2")},
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            return_value=(MagicMock(), mock_bucket, mock_client),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message",
            return_value=(None, None, query),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path",
            side_effect=[
                mock_example_parts["protocol1"],
                mock_example_parts["video1"],
                mock_example_parts["protocol2"],
                mock_example_parts["video2"],
            ],
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "success",
        "local_video_path": None,
        "gcs_video_path": None,
        "video_name": None,
        "remaining_message": query,
        "protocol": "# PCR Protocol\n\n## Abstract\n\nPCR amplification protocol.",
        "usage_metadata": {"input_tokens": 50, "output_tokens": 30},
        "protocol_generation_time": result["protocol_generation_time"],
        "metadata": {"word_count": "9", "input_type": "text"},
    }


# ============================================================================
# Tests for generate_protocols - Error Handling
# ============================================================================


def test_generate_protocols_returns_error_when_environment_validation_fails() -> None:
    """Test that generate_protocols returns error when EnvironmentValidator.load_environment raises ValueError."""
    # given
    query = "Create a protocol"

    with patch.object(
        agent.EnvironmentValidator,
        "load_environment",
        side_effect=ValueError("Missing required environment variables"),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Missing required environment variables",
    }


def test_generate_protocols_returns_error_when_cloud_resources_initialization_fails(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols returns error when EnvironmentValidator.initialize_cloud_resources raises CloudResourceError."""
    # given
    query = "Create a protocol"

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            side_effect=agent.CloudResourceError("Failed to connect to GCS"),
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Failed to connect to GCS",
    }


def test_generate_protocols_returns_error_when_generate_parts_from_folder_raises_os_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols returns error when utils.generate_parts_from_folder raises OSError."""
    # given
    query = "Create a protocol"

    mock_bucket = MagicMock()
    mock_client = MagicMock()

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            return_value=(MagicMock(), mock_bucket, mock_client),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder",
            side_effect=OSError("Permission denied accessing folder"),
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: Permission denied accessing folder",
    }


def test_generate_protocols_returns_error_when_generate_part_from_path_raises_value_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols returns error when utils.generate_part_from_path raises ValueError."""
    # given
    query = "Video path: /invalid/path.mp4"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            return_value=(MagicMock(), mock_bucket, mock_client),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message",
            return_value=("/invalid/path.mp4", "path.mp4", ""),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path",
            side_effect=ValueError("Invalid file path"),
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: Invalid file path",
    }


def test_generate_protocols_returns_error_when_generate_content_raises_type_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols returns error when client.models.generate_content raises TypeError."""
    # given
    query = "Create a protocol"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TypeError("Invalid content type")

    mock_example_parts = {
        "protocol1": {"part": types.Part.from_text(text="mock protocol1")},
        "video1": {"part": types.Part.from_text(text="mock video1")},
        "protocol2": {"part": types.Part.from_text(text="mock protocol2")},
        "video2": {"part": types.Part.from_text(text="mock video2")},
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            return_value=(MagicMock(), mock_bucket, mock_client),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message",
            return_value=(None, None, query),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path",
            side_effect=[
                mock_example_parts["protocol1"],
                mock_example_parts["video1"],
                mock_example_parts["protocol2"],
                mock_example_parts["video2"],
            ],
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: Invalid content type",
    }


def test_generate_protocols_returns_error_when_generate_content_raises_runtime_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols returns error when client.models.generate_content raises RuntimeError."""
    # given
    query = "Create a protocol"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API timeout")

    mock_example_parts = {
        "protocol1": {"part": types.Part.from_text(text="mock protocol1")},
        "video1": {"part": types.Part.from_text(text="mock video1")},
        "protocol2": {"part": types.Part.from_text(text="mock protocol2")},
        "video2": {"part": types.Part.from_text(text="mock video2")},
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    with (
        patch.object(
            agent.EnvironmentValidator, "load_environment", return_value=mock_env_vars
        ),
        patch.object(
            agent.EnvironmentValidator,
            "initialize_cloud_resources",
            return_value=(MagicMock(), mock_bucket, mock_client),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message",
            return_value=(None, None, query),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path",
            side_effect=[
                mock_example_parts["protocol1"],
                mock_example_parts["video1"],
                mock_example_parts["protocol2"],
                mock_example_parts["video2"],
            ],
        ),
    ):
        # when
        result = agent.generate_protocols(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: API timeout",
    }


# ============================================================================
# UNCOVERED TEST CASES (Lower Priority)
# ============================================================================
# Review these and decide which to implement:
#
# test_generate_protocols_handles_video_with_gcs_path
# """Test that generate_protocols processes video input when file_path is already a GCS URI."""
# value: 6/10 (edge case - GCS paths are already handled by utils, but worth testing integration)
# approach: adapt existing test test_generate_protocols_returns_success_with_video_input
#
# test_generate_protocols_handles_empty_metadata_from_video
# """Test that generate_protocols handles case when video metadata extraction fails and returns empty dict."""
# value: 5/10 (edge case - metadata extraction can fail but doesn't break main flow)
# approach: adapt existing test test_generate_protocols_returns_success_with_video_input
#
# test_generate_protocols_handles_query_with_special_characters
# """Test that generate_protocols handles text input with special characters and unicode."""
# value: 4/10 (edge case - special characters should be handled by the model)
# approach: create new test or adapt existing test_generate_protocols_returns_success_with_text_input
