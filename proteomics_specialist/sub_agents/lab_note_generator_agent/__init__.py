"""Lab note generator agent can convert videos into lab notes by comparing the procedure in videos with existing protocols."""

from .agent import lab_note_benchmark_helper_agent, lab_note_generator_agent

__all__ = ["lab_note_benchmark_helper_agent", "lab_note_generator_agent"]
