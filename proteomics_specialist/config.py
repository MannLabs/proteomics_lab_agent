"""Config file to define models."""

from dataclasses import dataclass


@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters.

    Attributes:
        critic_model (str): Model for evaluation tasks.
        worker_model (str): Model for working/generation tasks.
        max_search_iterations (int): Maximum search iterations allowed.

    """

    model: str = "gemini-2.5-flash"


config = ResearchConfiguration()
