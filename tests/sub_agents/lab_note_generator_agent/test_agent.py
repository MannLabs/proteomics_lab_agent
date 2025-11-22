"""Unit tests for lab_note_generator_agent.agent module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from proteomics_lab_agent.sub_agents.lab_note_generator_agent import agent

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_env_vars() -> dict[str, str]:
    """Provide mock environment variables for tests."""
    return {
        "model": "gemini-2.5-flash",
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test-bucket/knowledge",
        "example_protocol_path": "gs://test-bucket/protocol.pdf",
        "example_video_path": "gs://test-bucket/video.mp4",
        "example_lab_note_path": "gs://test-bucket/lab_note.pdf",
    }


# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.generate_part_from_path"
)
@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_generate_lab_notes_returns_success_with_protocol_from_tool_context(  # noqa: PLR0913
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_gen_part_path: MagicMock,
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_lab_notes successfully processes video with protocol from tool_context."""
    # given
    query = "Video path: /path/to/video.mp4. Analyze this lab procedure."
    protocol = "# Test Protocol\n\nStep 1: Do this\nStep 2: Do that"

    mock_tool_context = MagicMock()
    mock_tool_context.state.get.return_value = protocol

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "# Lab Notes\n\n## Aim\n\nTest lab notes content."
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/video.mp4",
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }
    mock_example_parts = {
        "protocol": {"part": types.Part.from_text(text="mock protocol")},
        "video": {"part": types.Part.from_text(text="mock video")},
        "lab_note": {"part": types.Part.from_text(text="mock lab note")},
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (
        "/path/to/video.mp4",
        "video.mp4",
        "Analyze this lab procedure.",
    )
    mock_gen_part_path.side_effect = [
        mock_example_parts["protocol"],
        mock_example_parts["video"],
        mock_example_parts["lab_note"],
        mock_video_part,
    ]

    # when
    result = agent.generate_lab_notes(query, mock_tool_context, protocol_input=None)

    # then
    assert result == {
        "status": "success",
        "local_video_path": "/path/to/video.mp4",
        "gcs_video_path": "gs://test-bucket/video.mp4",
        "video_name": "video.mp4",
        "remaining_message": "Analyze this lab procedure.",
        "protocol": protocol,
        "lab_notes": "# Lab Notes\n\n## Aim\n\nTest lab notes content.",
        "usage_metadata": {"input_tokens": 100, "output_tokens": 50},
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }
    mock_tool_context.state.get.assert_called_once_with("retrieved_protocol")


@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.generate_part_from_path"
)
@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_generate_lab_notes_returns_success_with_protocol_from_input(  # noqa: PLR0913
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_gen_part_path: MagicMock,
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_lab_notes successfully processes video with protocol from protocol_input parameter."""
    # given
    query = "Video path: /path/to/video.mp4. Analyze this lab procedure."
    protocol = "# Test Protocol\n\nStep 1: Do this\nStep 2: Do that"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "# Lab Notes\n\n## Aim\n\nTest lab notes content."
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/video.mp4",
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }
    mock_example_parts = {
        "protocol": {"part": types.Part.from_text(text="mock protocol")},
        "video": {"part": types.Part.from_text(text="mock video")},
        "lab_note": {"part": types.Part.from_text(text="mock lab note")},
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (
        "/path/to/video.mp4",
        "video.mp4",
        "Analyze this lab procedure.",
    )
    mock_gen_part_path.side_effect = [
        mock_example_parts["protocol"],
        mock_example_parts["video"],
        mock_example_parts["lab_note"],
        mock_video_part,
    ]

    # when
    result = agent.generate_lab_notes(query, None, protocol_input=protocol)

    # then
    assert result == {
        "status": "success",
        "local_video_path": "/path/to/video.mp4",
        "gcs_video_path": "gs://test-bucket/video.mp4",
        "video_name": "video.mp4",
        "remaining_message": "Analyze this lab procedure.",
        "protocol": protocol,
        "lab_notes": "# Lab Notes\n\n## Aim\n\nTest lab notes content.",
        "usage_metadata": {"input_tokens": 100, "output_tokens": 50},
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@patch.object(
    agent.EnvironmentValidator,
    "load_environment",
    side_effect=ValueError("Missing required environment variables"),
)
def test_generate_lab_notes_returns_error_when_environment_validation_fails(
    mock_load_env: MagicMock,  # noqa: ARG001
) -> None:
    """Test that generate_lab_notes returns error when EnvironmentValidator.load_environment raises ValueError."""
    # given
    query = "Video path: /path/to/video.mp4"

    # when
    result = agent.generate_lab_notes(query, None, protocol_input="Test protocol")

    # then
    assert result == {
        "status": "error",
        "error_message": "Missing required environment variables",
    }


@patch.object(
    agent.EnvironmentValidator,
    "initialize_cloud_resources",
    side_effect=agent.CloudResourceError("Failed to connect to GCS"),
)
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_generate_lab_notes_returns_error_when_cloud_resources_initialization_fails(
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,  # noqa: ARG001
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_lab_notes returns error when EnvironmentValidator.initialize_cloud_resources raises CloudResourceError."""
    # given
    query = "Video path: /path/to/video.mp4"
    mock_load_env.return_value = mock_env_vars

    # when
    result = agent.generate_lab_notes(query, None, protocol_input="Test protocol")

    # then
    assert result == {
        "status": "error",
        "error_message": "Failed to connect to GCS",
    }


@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.lab_note_generator_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_generate_lab_notes_returns_error_when_no_file_path_extracted(
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_lab_notes returns error when extract_file_path_and_message returns None for file_path."""
    # given
    query = "Invalid query without proper file path"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (None, None, query)

    # when
    result = agent.generate_lab_notes(query, None, protocol_input="Test protocol")

    # then
    assert result == {
        "status": "error",
        "error_message": "Could not extract valid file path from query",
    }
