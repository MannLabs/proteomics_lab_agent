# API Reference

This is the auto-generated API reference for `proteomics_lab_agent`.

## Configuration & Utils

These are the main configuration classes and utility functions for the agent.

```{eval-rst}
.. module:: proteomics_lab_agent.config
.. currentmodule:: proteomics_lab_agent

.. autosummary::
   :toctree: generated
   :nosignatures:

   config.ResearchConfiguration
   config.get_current_datetime
   config.extract_file_path_and_message
   config.generate_parts_from_path
   config.generate_parts_from_folder
   config.get_blob_name_from_gcs_path
   config.upload_file_from_path_to_gcs

## Main Agent
The root agent and workflow definition.

.. module:: proteomics_lab_agent.agent
.. currentmodule:: proteomics_lab_agent

.. autosummary::
   :toctree: generated
   :nosignatures:

   agent.ProteomicsLabAgent
   agent.create_workflow
   agent.route_question
   agent.State
   agent.Tool

## Sub-Agents
These are the specialized agents called by the main workflow.

.. module:: proteomics_lab_agent.sub_agents
.. currentmodule:: proteomics_lab_agent

.. autosummary::
   :toctree: generated
   :nosignatures:

   sub_agents.instrument_agent.run_instrument_agent
   sub_agents.lab_knowledge_agent.run_lab_knowledge_agent
   sub_agents.lab_note_generator_agent.run_lab_note_generator
   sub_agents.protocol_generator_agent.run_protocol_generator
   sub_agents.qc_memory_agent.run_qc_memory_agent
   sub_agents.video_analyzer_agent.run_video_analyzer

## Prompt Engineering

.. module:: proteomics_lab_agent.prompt
.. currentmodule:: proteomics_lab_agent

.. autosummary::
   :toctree: generated
   :nosignatures:

   prompt.get_system_prompt
   prompt.get_user_prompt
