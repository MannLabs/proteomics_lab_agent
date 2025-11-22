"""Unit tests for protocol_generator_agent.agent module."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch

from google.genai import types

from proteomics_lab_agent.sub_agents.protocol_generator_agent import agent

# ============================================================================
# Tests for generate_protocols - Happy Path
# ============================================================================


@patch(
    "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path"
)
@patch(
    "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_generate_protocols_returns_success_with_video_input(  # noqa: PLR0913
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_gen_part_path: MagicMock,
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

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (
        "/path/to/video.mp4",
        "video.mp4",
        "Analyze this video.",
    )
    mock_gen_part_path.side_effect = [
        mock_example_parts["protocol1"],
        mock_example_parts["video1"],
        mock_example_parts["protocol2"],
        mock_example_parts["video2"],
        mock_video_part,
    ]

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
        "protocol_generation_time": ANY,
        "metadata": {"duration": "10.5", "file_size": "1024", "input_type": "video"},
    }

    assert result["protocol_generation_time"] > 0


@patch(
    "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_part_from_path"
)
@patch(
    "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.extract_file_path_and_message"
)
@patch(
    "proteomics_lab_agent.sub_agents.protocol_generator_agent.agent.utils.generate_parts_from_folder"
)
@patch.object(agent.EnvironmentValidator, "initialize_cloud_resources")
@patch.object(agent.EnvironmentValidator, "load_environment")
def test_generate_protocols_returns_success_with_text_input(  # noqa: PLR0913
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,
    mock_gen_parts_folder: MagicMock,
    mock_extract_file: MagicMock,
    mock_gen_part_path: MagicMock,
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

    mock_load_env.return_value = mock_env_vars
    mock_init_cloud.return_value = (MagicMock(), mock_bucket, mock_client)
    mock_gen_parts_folder.return_value = mock_background_parts
    mock_extract_file.return_value = (None, None, query)
    mock_gen_part_path.side_effect = [
        mock_example_parts["protocol1"],
        mock_example_parts["video1"],
        mock_example_parts["protocol2"],
        mock_example_parts["video2"],
    ]

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
        "protocol_generation_time": ANY,
        "metadata": {"word_count": "9", "input_type": "text"},
    }

    assert result["protocol_generation_time"] > 0


# ============================================================================
# Tests for generate_protocols - Error Handling
# ============================================================================


@patch.object(
    agent.EnvironmentValidator,
    "load_environment",
    side_effect=ValueError("Missing required environment variables"),
)
def test_generate_protocols_returns_error_when_environment_validation_fails(
    mock_load_env: MagicMock,  # noqa: ARG001
) -> None:
    """Test that generate_protocols returns error when EnvironmentValidator.load_environment raises ValueError."""
    # given
    query = "Create a protocol"

    # when
    result = agent.generate_protocols(query)

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
def test_generate_protocols_returns_error_when_cloud_resources_initialization_fails(
    mock_load_env: MagicMock,
    mock_init_cloud: MagicMock,  # noqa: ARG001
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols returns error when EnvironmentValidator.initialize_cloud_resources raises CloudResourceError."""
    # given
    query = "Create a protocol"
    mock_load_env.return_value = mock_env_vars

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
# Tests for generate_protocols - Edge Cases
# ============================================================================


def test_generate_protocols_handles_video_with_gcs_path(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols processes video input when file_path is already a GCS URI."""
    # given
    query = "gs://test-bucket/input_video/sample.mp4"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "# Protocol from GCS Video\n\n## Abstract\n\nGCS video protocol."
    )
    mock_response.usage_metadata = {"input_tokens": 120, "output_tokens": 60}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock gcs video"),
        "gcs_uri": "gs://test-bucket/input_video/sample.mp4",
        "metadata": {"duration": "15.2", "file_size": "2048", "input_type": "video"},
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
            return_value=(
                "gs://test-bucket/input_video/sample.mp4",
                "sample.mp4",
                "",
            ),
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
        "local_video_path": "gs://test-bucket/input_video/sample.mp4",
        "gcs_video_path": "gs://test-bucket/input_video/sample.mp4",
        "video_name": "sample.mp4",
        "remaining_message": query,
        "protocol": "# Protocol from GCS Video\n\n## Abstract\n\nGCS video protocol.",
        "usage_metadata": {"input_tokens": 120, "output_tokens": 60},
        "protocol_generation_time": ANY,
        "metadata": {"duration": "15.2", "file_size": "2048", "input_type": "video"},
    }

    assert result["protocol_generation_time"] > 0


def test_generate_protocols_handles_empty_metadata_from_video(
    mock_env_vars: dict[str, str],
) -> None:
    """Test that generate_protocols handles case when video metadata extraction fails and returns empty dict."""
    # given
    query = "Video path: /path/to/corrupted.mp4"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "# Protocol Title\n\n## Abstract\n\nProtocol despite missing metadata."
    )
    mock_response.usage_metadata = {"input_tokens": 90, "output_tokens": 45}
    mock_client.models.generate_content.return_value = mock_response

    mock_video_part = {
        "part": types.Part.from_text(text="mock video"),
        "gcs_uri": "gs://test-bucket/corrupted.mp4",
        "metadata": {},
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
            return_value=("/path/to/corrupted.mp4", "corrupted.mp4", ""),
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
        "local_video_path": "/path/to/corrupted.mp4",
        "gcs_video_path": "gs://test-bucket/corrupted.mp4",
        "video_name": "corrupted.mp4",
        "remaining_message": query,
        "protocol": "# Protocol Title\n\n## Abstract\n\nProtocol despite missing metadata.",
        "usage_metadata": {"input_tokens": 90, "output_tokens": 45},
        "protocol_generation_time": ANY,
        "metadata": {},
    }
    assert result["protocol_generation_time"] > 0


# ============================================================================
# AGENT INSTANTIATION TESTS
# ============================================================================


def test_protocol_generator_agent_instantiation() -> None:
    """Test that protocol_generator_agent is instantiated correctly with all expected attributes."""
    # given/when
    from proteomics_lab_agent.config import config

    # then
    assert agent.protocol_generator_agent.name == "protocol_generator_agent"
    assert (
        agent.protocol_generator_agent.description
        == "Agent converts text input or video files into protocols."
    )
    assert agent.protocol_generator_agent.model == config.model
    assert "Path A" in agent.protocol_generator_agent.instruction
    assert "Path B" in agent.protocol_generator_agent.instruction
    assert "generate_protocols" in agent.protocol_generator_agent.instruction
    assert len(agent.protocol_generator_agent.tools) == 1
    assert agent.protocol_generator_agent.tools[0] == agent.generate_protocols
    assert agent.protocol_generator_agent.output_key == "protocol_result"
