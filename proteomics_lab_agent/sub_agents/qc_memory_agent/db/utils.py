"""Utility constants and exceptions for the QC Memory Agent database operations."""

from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "database.db"
GRADIENT_TOLERANCE = (
    0.001  # Tolerance for retrieving raw files based on gradient length
)
MAX_PERFORMANCE_RATING = 5
COMPATIBLE_SCHEMA_VERSION = 1
AGENT_NAME = "qc_memory_agent_v1.0"


class DatabaseError(Exception):
    """Custom exception for database operations."""


class ValidationError(DatabaseError):
    """Exception for data validation errors."""
