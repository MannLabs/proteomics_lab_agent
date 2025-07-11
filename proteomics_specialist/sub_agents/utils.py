"""Helper functions for subagents."""

import os


def get_required_env(var_name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value
