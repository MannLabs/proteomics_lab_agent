"""Unit tests for video_analyzer_agent.agent module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from google.genai import types

from proteomics_lab_agent.sub_agents.video_analyzer_agent import agent

# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


@patch(
    "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_part_from_path"
)
@patch(
    "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_analyze_proteomics_video_returns_success_with_valid_video(  # noqa: PLR0913
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_gen_part_path: MagicMock,
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video successfully processes valid video input."""
    # given
    query = "Video path: /path/to/video.mp4. Analyze this proteomics procedure."

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "The video shows a protein extraction procedure using standard lab equipment."
    )
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/input_video/video.mp4",
    }
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (
        "/path/to/video.mp4",
        "video.mp4",
        "Analyze this proteomics procedure.",
    )
    mock_gen_part_path.return_value = mock_video_part

    # when
    result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "success",
        "local_video_path": "/path/to/video.mp4",
        "gcs_video_path": "gs://test-bucket/input_video/video.mp4",
        "video_name": "video.mp4",
        "remaining_message": "Analyze this proteomics procedure.",
        "video_analysis": "The video shows a protein extraction procedure using standard lab equipment.",
        "usage_metadata": {"input_tokens": 100, "output_tokens": 50},
    }


# ============================================================================
# ERROR CASE TESTS
# ============================================================================


@patch.object(
    agent.EnvironmentValidator,
    "load_environment",
    side_effect=ValueError("Missing required environment variables"),
)
def test_analyze_proteomics_video_returns_error_when_environment_validation_fails(
    mock_load_env: MagicMock,  # noqa: ARG001
) -> None:
    """Test that analyze_proteomics_video returns error when EnvironmentValidator.load_environment raises ValueError."""
    # given
    query = "Video path: /path/to/video.mp4"

    # when
    result = agent.analyze_proteomics_video(query)

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
def test_analyze_proteomics_video_returns_error_when_cloud_resources_initialization_fails(
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,  # noqa: ARG001
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video returns error when EnvironmentValidator.initialize_cloud_resources raises CloudResourceError."""
    # given
    query = "Video path: /path/to/video.mp4"
    mock_load_env.return_value = mock_env_vars

    # when
    result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Failed to connect to GCS",
    }


@patch(
    "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_analyze_proteomics_video_returns_error_when_no_file_path_extracted(
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video returns error when extract_file_path_and_message returns no file path."""
    # given
    query = "Analyze this video"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_background_parts = {"parts": [types.Part.from_text(text="mock background")]}

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (None, None, query)

    # when
    result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Could not extract valid file path from query",
    }


def test_analyze_proteomics_video_returns_error_when_generate_parts_from_folder_raises_os_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video returns error when utils.generate_parts_from_folder raises OSError."""
    # given
    query = "Video path: /path/to/video.mp4"

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
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder",
            side_effect=OSError("Permission denied accessing folder"),
        ),
    ):
        # when
        result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: Permission denied accessing folder",
    }


def test_analyze_proteomics_video_returns_error_when_generate_part_from_path_raises_value_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video returns error when utils.generate_part_from_path raises ValueError."""
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
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.extract_file_path_and_message",
            return_value=("/invalid/path.mp4", "path.mp4", ""),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_part_from_path",
            side_effect=ValueError("Invalid file path"),
        ),
    ):
        # when
        result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: Invalid file path",
    }


def test_analyze_proteomics_video_returns_error_when_generate_content_raises_type_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video returns error when client.models.generate_content raises TypeError."""
    # given
    query = "Video path: /path/to/video.mp4"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TypeError("Invalid content type")

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/video.mp4",
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
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.extract_file_path_and_message",
            return_value=("/path/to/video.mp4", "video.mp4", ""),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_part_from_path",
            return_value=mock_video_part,
        ),
    ):
        # when
        result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: Invalid content type",
    }


def test_analyze_proteomics_video_returns_error_when_generate_content_raises_runtime_error(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video returns error when client.models.generate_content raises RuntimeError."""
    # given
    query = "Video path: /path/to/video.mp4"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API timeout")

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/video.mp4",
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
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.extract_file_path_and_message",
            return_value=("/path/to/video.mp4", "video.mp4", ""),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_part_from_path",
            return_value=mock_video_part,
        ),
    ):
        # when
        result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "error",
        "error_message": "Analysis failed: API timeout",
    }


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_analyze_proteomics_video_handles_video_with_gcs_path(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that analyze_proteomics_video processes video input when file_path is already a GCS URI."""
    # given
    query = "gs://test-bucket/input_video/sample.mp4"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "The video demonstrates a mass spectrometry sample preparation workflow."
    )
    mock_response.usage_metadata = {"input_tokens": 120, "output_tokens": 60}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock gcs video"),
        "gcs_uri": "gs://test-bucket/input_video/sample.mp4",
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
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_parts_from_folder",
            return_value=mock_background_parts,
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.extract_file_path_and_message",
            return_value=(
                "gs://test-bucket/input_video/sample.mp4",
                "sample.mp4",
                "",
            ),
        ),
        patch(
            "proteomics_lab_agent.sub_agents.video_analyzer_agent.agent.utils.generate_part_from_path",
            return_value=mock_video_part,
        ),
    ):
        # when
        result = agent.analyze_proteomics_video(query)

    # then
    assert result == {
        "status": "success",
        "local_video_path": "gs://test-bucket/input_video/sample.mp4",
        "gcs_video_path": "gs://test-bucket/input_video/sample.mp4",
        "video_name": "sample.mp4",
        "remaining_message": "",
        "video_analysis": "The video demonstrates a mass spectrometry sample preparation workflow.",
        "usage_metadata": {"input_tokens": 120, "output_tokens": 60},
    }


# ============================================================================
# AGENT INSTANTIATION TESTS
# ============================================================================


def test_video_analyzer_agent_instantiation() -> None:
    """Test that video_analyzer_agent is instantiated correctly with all expected attributes."""
    # given/when
    from proteomics_lab_agent.config import config

    # then
    assert agent.video_analyzer_agent.name == "video_analyzer_agent"
    assert agent.video_analyzer_agent.description == "Agent analyzes video files."
    assert agent.video_analyzer_agent.model == config.model
    assert (
        "Always analyse the user query by invoking the tool"
        in agent.video_analyzer_agent.instruction
    )
    assert "analyze_proteomics_video" in agent.video_analyzer_agent.instruction
    assert len(agent.video_analyzer_agent.tools) == 1
    assert agent.video_analyzer_agent.tools[0] == agent.analyze_proteomics_video
