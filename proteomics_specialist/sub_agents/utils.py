"""Helper functions for subagents."""

import configparser
from pathlib import Path

config = configparser.ConfigParser()

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
secrets_path = project_root / "secrets.ini"

config.read(secrets_path)


def get_required_env(var_name: str) -> str:
    """Get required environment variable or raise error."""
    value = config["DEFAULT"][var_name]
    if value is None:
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value
