"""Config file to define models."""

from dataclasses import dataclass


@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters.

    Attributes:
        model (str): Model for generation tasks.
        analysis_model (str): Model for video analysis tasks.
        temperature (float): Controls randomness in model outputs. Higher values (0.7-1.0)
            produce more creative/varied responses, lower values (0.1-0.3) produce more
            deterministic responses.

    """

    model: str = "gemini-2.5-flash"
    analysis_model: str = "gemini-2.5-pro"
    temperature: float = 0.9


config = ResearchConfiguration()
