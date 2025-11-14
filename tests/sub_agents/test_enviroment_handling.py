"""Unit tests for enviroment_handling module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from proteomics_lab_agent.sub_agents.enviroment_handling import (
    CloudResourceError,
    EnvironmentValidator,
    get_env_var,
)

# ============================================================================
# HAPPY PATH TESTS
# ============================================================================


def test_get_env_var_returns_value_when_set() -> None:
    """Test that get_env_var returns the value when environment variable is set."""
    # given
    with patch(
        "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
    ) as mock_getenv:
        mock_getenv.return_value = "test_value"

        # when
        result = get_env_var("TEST_VAR")

        # then
        assert result == "test_value"
        mock_getenv.assert_called_once_with("TEST_VAR")


def test_validate_env_returns_empty_list_when_all_vars_present() -> None:
    """Test that validate_env returns empty list when all required variables are present."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test/knowledge",
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "video_analyzer")

    # then
    assert missing == []


def test_load_environment_returns_dict_with_all_vars_for_video_analyzer() -> None:
    """Test that load_environment returns complete dictionary for video_analyzer agent."""
    # given
    mock_config = MagicMock(spec=["model", "temperature"])
    mock_config.model = "gemini-2.5-flash"
    mock_config.temperature = 0.9

    env_dict = {
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "KNOWLEDGE_BASE_PATH": "gs://test/knowledge",
    }

    with (
        patch("proteomics_lab_agent.sub_agents.enviroment_handling.load_dotenv"),
        patch(
            "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
        ) as mock_getenv,
    ):
        mock_getenv.side_effect = lambda key: env_dict.get(key)

        # when
        result = EnvironmentValidator.load_environment("video_analyzer", mock_config)

        # then
        assert result == {
            "model": "gemini-2.5-flash",
            "temperature": 0.9,
            "bucket_name": "test-bucket",
            "project_id": "test-project",
            "knowledge_base_path": "gs://test/knowledge",
        }


def test_load_environment_returns_dict_with_all_vars_for_protocol_generator() -> None:
    """Test that load_environment returns complete dictionary for protocol_generator agent."""
    # given
    mock_config = MagicMock(spec=["model", "temperature"])
    mock_config.model = "gemini-2.5-flash"
    mock_config.temperature = 0.9

    env_dict = {
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "KNOWLEDGE_BASE_PATH": "gs://test/knowledge",
        "EXAMPLE_PROTOCOL1_PATH": "gs://test/protocol1.pdf",
        "EXAMPLE_VIDEO1_PATH": "gs://test/video1.mp4",
        "EXAMPLE_PROTOCOL2_PATH": "gs://test/protocol2.pdf",
        "EXAMPLE_VIDEO2_PATH": "gs://test/video2.mp4",
    }

    with (
        patch("proteomics_lab_agent.sub_agents.enviroment_handling.load_dotenv"),
        patch(
            "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
        ) as mock_getenv,
    ):
        mock_getenv.side_effect = lambda key: env_dict.get(key)

        # when
        result = EnvironmentValidator.load_environment(
            "protocol_generator", mock_config
        )

        # then
        assert result == {
            "model": "gemini-2.5-flash",
            "temperature": 0.9,
            "bucket_name": "test-bucket",
            "project_id": "test-project",
            "knowledge_base_path": "gs://test/knowledge",
            "example_protocol1_path": "gs://test/protocol1.pdf",
            "example_video1_path": "gs://test/video1.mp4",
            "example_protocol2_path": "gs://test/protocol2.pdf",
            "example_video2_path": "gs://test/video2.mp4",
        }


def test_initialize_cloud_resources_returns_tuple_with_clients() -> None:
    """Test that initialize_cloud_resources successfully returns storage client, bucket, and genai client."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
    }

    mock_storage_client = MagicMock()
    mock_bucket = MagicMock()
    mock_genai_client = MagicMock()

    with (
        patch("google.cloud.storage.Client") as mock_storage,
        patch("google.genai.Client") as mock_genai,
    ):
        mock_storage.return_value = mock_storage_client
        mock_storage_client.bucket.return_value = mock_bucket
        mock_genai.return_value = mock_genai_client

        # when
        storage_client, bucket, client = (
            EnvironmentValidator.initialize_cloud_resources(env_vars)
        )

        # then
        assert storage_client == mock_storage_client
        assert bucket == mock_bucket
        assert client == mock_genai_client
        mock_storage_client.bucket.assert_called_once_with("test-bucket")
        mock_genai.assert_called_once_with(
            vertexai=True, project="test-project", location="us-central1"
        )


# ============================================================================
# ERROR CASE TESTS
# ============================================================================


def test_get_env_var_raises_value_error_when_not_set() -> None:
    """Test that get_env_var raises ValueError when environment variable is not set."""
    # given
    with patch(
        "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
    ) as mock_getenv:
        mock_getenv.return_value = None

        # when / then
        with pytest.raises(
            ValueError, match="TEST_VAR environment variable is not set"
        ):
            get_env_var("TEST_VAR")


def test_get_env_var_raises_value_error_when_empty_string() -> None:
    """Test that get_env_var raises ValueError when environment variable is empty string."""
    # given
    with patch(
        "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
    ) as mock_getenv:
        mock_getenv.return_value = ""

        # when / then
        with pytest.raises(
            ValueError, match="TEST_VAR environment variable is not set"
        ):
            get_env_var("TEST_VAR")


def test_validate_env_returns_missing_common_vars() -> None:
    """Test that validate_env identifies missing common environment variables."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": None,
        "knowledge_base_path": None,
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "video_analyzer")

    # then
    assert missing == ["GOOGLE_CLOUD_PROJECT", "KNOWLEDGE_BASE_PATH"]


def test_validate_env_returns_missing_agent_specific_vars() -> None:
    """Test that validate_env identifies missing agent-specific environment variables."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test/knowledge",
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
        "example_protocol1_path": "gs://test/protocol1.pdf",
        "example_video1_path": None,
        "example_protocol2_path": None,
        "example_video2_path": "gs://test/video2.mp4",
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "protocol_generator")

    # then
    assert "EXAMPLE_VIDEO1_PATH" in missing
    assert "EXAMPLE_PROTOCOL2_PATH" in missing


def test_validate_env_returns_missing_model_config() -> None:
    """Test that validate_env identifies missing model configuration."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test/knowledge",
        "model": None,
        "temperature": 0.9,
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "video_analyzer")

    # then
    assert "model or temperature configuration" in missing


def test_validate_env_returns_missing_temperature_config() -> None:
    """Test that validate_env identifies missing temperature configuration."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test/knowledge",
        "model": "gemini-2.5-flash",
        "temperature": None,
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "video_analyzer")

    # then
    assert "model or temperature configuration" in missing


def test_load_environment_raises_value_error_when_missing_vars() -> None:
    """Test that load_environment raises ValueError when required environment variables are missing."""
    # given
    mock_config = MagicMock()
    mock_config.model = "gemini-2.5-flash"
    mock_config.temperature = 0.9

    env_dict = {
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
        "GOOGLE_CLOUD_PROJECT": None,
        "KNOWLEDGE_BASE_PATH": None,
    }

    with (
        patch("proteomics_lab_agent.sub_agents.enviroment_handling.load_dotenv"),
        patch(
            "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
        ) as mock_getenv,
    ):
        mock_getenv.side_effect = lambda key: env_dict.get(key)

        # when / then
        with pytest.raises(
            ValueError,
            match=r"Missing required environment variables for video_analyzer: GOOGLE_CLOUD_PROJECT, KNOWLEDGE_BASE_PATH",
        ):
            EnvironmentValidator.load_environment("video_analyzer", mock_config)


def test_initialize_cloud_resources_raises_error_when_storage_client_fails() -> None:
    """Test that initialize_cloud_resources raises CloudResourceError when storage client initialization fails."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
    }

    # when / then
    with (
        patch(
            "google.cloud.storage.Client",
            side_effect=Exception("Storage connection failed"),
        ),
        pytest.raises(
            CloudResourceError,
            match="Failed to initialize cloud resources: Storage connection failed",
        ),
    ):
        EnvironmentValidator.initialize_cloud_resources(env_vars)


def test_initialize_cloud_resources_raises_error_when_genai_client_fails() -> None:
    """Test that initialize_cloud_resources raises CloudResourceError when genai client initialization fails."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
    }

    mock_storage_client = MagicMock()
    mock_bucket = MagicMock()

    with (
        patch("google.cloud.storage.Client") as mock_storage,
        patch(
            "google.genai.Client",
            side_effect=Exception("GenAI connection failed"),
        ),
    ):
        mock_storage.return_value = mock_storage_client
        mock_storage_client.bucket.return_value = mock_bucket

        # when / then
        with pytest.raises(
            CloudResourceError,
            match="Failed to initialize cloud resources: GenAI connection failed",
        ):
            EnvironmentValidator.initialize_cloud_resources(env_vars)


def test_initialize_cloud_resources_raises_error_when_bucket_name_missing() -> None:
    """Test that initialize_cloud_resources raises CloudResourceError when bucket_name is missing from env_vars."""
    # given
    env_vars = {
        "project_id": "test-project",
    }

    # when / then
    with (
        patch("google.cloud.storage.Client"),
        pytest.raises(CloudResourceError, match="Invalid configuration:"),
    ):
        EnvironmentValidator.initialize_cloud_resources(env_vars)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_load_environment_uses_analysis_model_when_available() -> None:
    """Test that load_environment prefers analysis_model over model attribute."""
    # given
    mock_config = MagicMock()
    mock_config.analysis_model = "gemini-2.5-pro"
    mock_config.model = "gemini-2.5-flash"
    mock_config.temperature = 0.9

    env_dict = {
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "KNOWLEDGE_BASE_PATH": "gs://test/knowledge",
    }

    with (
        patch("proteomics_lab_agent.sub_agents.enviroment_handling.load_dotenv"),
        patch(
            "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
        ) as mock_getenv,
    ):
        mock_getenv.side_effect = lambda key: env_dict.get(key)

        # when
        result = EnvironmentValidator.load_environment("video_analyzer", mock_config)

        # then
        assert result["model"] == "gemini-2.5-pro"


def test_load_environment_handles_lab_note_generator_agent_type() -> None:
    """Test that load_environment correctly handles lab_note_generator agent type."""
    # given
    mock_config = MagicMock()
    mock_config.model = "gemini-2.5-flash"
    mock_config.temperature = 0.9

    env_dict = {
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "KNOWLEDGE_BASE_PATH": "gs://test/knowledge",
        "EXAMPLE_PROTOCOL_PATH": "gs://test/protocol.pdf",
        "EXAMPLE_VIDEO_PATH": "gs://test/video.mp4",
        "EXAMPLE_LAB_NOTE_PATH": "gs://test/lab_note.md",
    }

    with (
        patch("proteomics_lab_agent.sub_agents.enviroment_handling.load_dotenv"),
        patch(
            "proteomics_lab_agent.sub_agents.enviroment_handling.os.getenv"
        ) as mock_getenv,
    ):
        mock_getenv.side_effect = lambda key: env_dict.get(key)

        # when
        result = EnvironmentValidator.load_environment(
            "lab_note_generator", mock_config
        )

        # then
        assert result["example_protocol_path"] == "gs://test/protocol.pdf"
        assert result["example_video_path"] == "gs://test/video.mp4"
        assert result["example_lab_note_path"] == "gs://test/lab_note.md"


def test_validate_env_handles_unknown_agent_type() -> None:
    """Test that validate_env handles unknown agent type gracefully (only validates common vars)."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
        "knowledge_base_path": "gs://test/knowledge",
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "unknown_agent")

    # then
    assert missing == []


def test_validate_env_returns_all_missing_vars_when_multiple_missing() -> None:
    """Test that validate_env returns all missing variables when multiple are missing."""
    # given
    env_vars = {
        "bucket_name": None,
        "project_id": None,
        "knowledge_base_path": None,
        "model": None,
        "temperature": None,
    }

    # when
    missing = EnvironmentValidator.validate_env(env_vars, "video_analyzer")

    # then
    assert "GOOGLE_CLOUD_STORAGE_BUCKET" in missing
    assert "GOOGLE_CLOUD_PROJECT" in missing
    assert "KNOWLEDGE_BASE_PATH" in missing
    assert "model or temperature configuration" in missing


def test_initialize_cloud_resources_uses_correct_genai_location() -> None:
    """Test that initialize_cloud_resources uses us-central1 as the location for genai client."""
    # given
    env_vars = {
        "bucket_name": "test-bucket",
        "project_id": "test-project",
    }

    mock_storage_client = MagicMock()
    mock_bucket = MagicMock()
    mock_genai_client = MagicMock()

    with (
        patch("google.cloud.storage.Client") as mock_storage,
        patch("google.genai.Client") as mock_genai,
    ):
        mock_storage.return_value = mock_storage_client
        mock_storage_client.bucket.return_value = mock_bucket
        mock_genai.return_value = mock_genai_client

        # when
        EnvironmentValidator.initialize_cloud_resources(env_vars)

        # then
        mock_genai.assert_called_once_with(
            vertexai=True, project="test-project", location="us-central1"
        )


# ============================================================================
# UNCOVERED TEST CASES
# ============================================================================
# Review these and decide which to implement:
#
# test_load_environment_calls_load_dotenv
# """Test that load_environment calls load_dotenv to load .env file."""
# value: 6/10 (verifies correct initialization flow)
# approach: use mock to verify load_dotenv is called
#
# test_get_env_var_handles_whitespace_only_value
# """Test that get_env_var treats whitespace-only values as empty."""
# value: 5/10 (edge case for string validation)
# approach: test with value like "   " or "\t\n"
#
# test_validate_env_handles_temperature_zero
# """Test that validate_env correctly handles temperature=0 (valid but falsy)."""
# value: 8/10 (important edge case - 0 is valid but falsy in Python)
# approach: test with temperature: 0 and verify it's not flagged as missing
#
# test_cloud_resource_error_is_proper_exception_subclass
# """Test that CloudResourceError is properly defined as Exception subclass."""
# value: 3/10 (basic class structure test)
# approach: verify isinstance and exception hierarchy
#
# test_load_environment_handles_config_without_model_attribute
# """Test that load_environment handles config object without model attribute."""
# value: 7/10 (robustness test for config variations)
# approach: test with config that has neither analysis_model nor model
#
# test_initialize_cloud_resources_with_different_project_ids
# """Test that initialize_cloud_resources correctly passes project_id to genai client."""
# value: 4/10 (already covered in happy path test)
# approach: parametrize test with different project IDs
