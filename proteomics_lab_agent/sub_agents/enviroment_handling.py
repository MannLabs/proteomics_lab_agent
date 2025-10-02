"""Unified environment variable validation for all proteomics agents."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar

from dotenv import load_dotenv

if TYPE_CHECKING:
    from proteomics_lab_agent.config import ResearchConfiguration


def get_env_var(var_name: str) -> str:
    """Validate that an environment variable is set and not empty."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"{var_name} environment variable is not set")
    return value


class CloudResourceError(Exception):
    """Custom exception for cloud resource initialization failures."""


class EnvironmentValidator:
    """Centralized environment variable validation for all agents."""

    COMMON_VARS: ClassVar[dict[str, str]] = {
        "bucket_name": "GOOGLE_CLOUD_STORAGE_BUCKET",
        "project_id": "GOOGLE_CLOUD_PROJECT",
        "knowledge_base_path": "KNOWLEDGE_BASE_PATH",
    }

    AGENT_SPECIFIC_VARS: ClassVar[dict[str, dict[str, str]]] = {
        "lab_note_generator": {
            "example_protocol_path": "EXAMPLE_PROTOCOL_PATH",
            "example_video_path": "EXAMPLE_VIDEO_PATH",
            "example_lab_note_path": "EXAMPLE_LAB_NOTE_PATH",
        },
        "protocol_generator": {
            "example_protocol1_path": "EXAMPLE_PROTOCOL1_PATH",
            "example_video1_path": "EXAMPLE_VIDEO1_PATH",
            "example_protocol2_path": "EXAMPLE_PROTOCOL2_PATH",
            "example_video2_path": "EXAMPLE_VIDEO2_PATH",
        },
        "video_analyzer": {
            # No additional specific variables needed
        },
    }

    @classmethod
    def load_environment(
        cls,
        agent_type: str,
        config: ResearchConfiguration,
    ) -> dict[str, str | None]:
        """Load and validate environment variables for a specific agent.

        Parameters
        ----------
        agent_type : str
            Type of agent ('lab_note_generator', 'protocol_generator', 'video_analyzer')
        config : Any
            Configuration object containing model and temperature settings

        Returns
        -------
        dict[str, str | None]
            Dictionary containing all required environment variables and config values

        Raises
        ------
        ValueError
            If required environment variables are missing

        """
        load_dotenv()

        env_vars = {
            "model": getattr(config, "analysis_model", None)
            or getattr(config, "model", None),
            "temperature": getattr(config, "temperature", None),
        }

        env_vars.update(
            {key: os.getenv(env_name) for key, env_name in cls.COMMON_VARS.items()}
        )

        if agent_type in cls.AGENT_SPECIFIC_VARS:
            for key, env_name in cls.AGENT_SPECIFIC_VARS[agent_type].items():
                env_vars[key] = os.getenv(env_name)

        missing_vars = cls.validate_env(env_vars, agent_type)

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables for {agent_type}: {', '.join(missing_vars)}"
            )

        return env_vars

    @classmethod
    def validate_env(
        cls, env_vars: dict[str, str | None], agent_type: str
    ) -> list[str]:
        """Validate environment variables and return missing ones.

        Parameters
        ----------
        env_vars : dict[str, str | None]
            Dictionary of environment variables to validate
        agent_type : str
            Type of agent being validated

        Returns
        -------
        list[str]
            List of missing environment variable names

        """
        missing_vars = []

        for key, env_name in cls.COMMON_VARS.items():
            if not env_vars.get(key):
                missing_vars.append(env_name)

        if agent_type in cls.AGENT_SPECIFIC_VARS:
            for key, env_name in cls.AGENT_SPECIFIC_VARS[agent_type].items():
                if not env_vars.get(key):
                    missing_vars.append(env_name)

        if not env_vars.get("model") or env_vars.get("temperature") is None:
            missing_vars.append("model or temperature configuration")

        return missing_vars

    @classmethod
    def initialize_cloud_resources(cls, env_vars: dict[str, str | None]) -> tuple:
        """Initialize Google Cloud resources.

        Parameters
        ----------
        env_vars : dict[str, str | None]
            Dictionary containing environment variables

        Returns
        -------
        tuple
            (storage_client, bucket, genai_client) tuple

        Raises
        ------
        CloudResourceError
            If cloud resources fail to initialize

        """
        from google import genai
        from google.cloud import storage

        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(env_vars["bucket_name"])
            client = genai.Client(
                vertexai=True, project=env_vars["project_id"], location="us-central1"
            )
        except (KeyError, ValueError) as e:
            raise CloudResourceError(f"Invalid configuration: {e}") from e
        except Exception as e:
            raise CloudResourceError(
                f"Failed to initialize cloud resources: {e}"
            ) from e
        else:
            return storage_client, bucket, client
