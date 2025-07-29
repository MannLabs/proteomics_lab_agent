"""Prompt templates for custom evaluator and evaluation set converter.

This module contains prompt templates used for extracting protocol titles and video URIs
from text responses in the evaluation pipeline.
"""

CUSTOM_EVALUATOR_EXTRACTION_PROMPT_TEMPLATE = """
You are a protocol title extraction expert. Your task is to identify and extract protocol titles from text responses.

Look for protocol titles that are typically:
- Enclosed in quotes
- Mentioned after words like "protocol", "found", "titled", "called", etc.
- The main protocol(s) being referenced in the response

Text to analyze: {response_text}

Extract the protocol title(s) and return your response in the following JSON format:

If there's one clear main protocol:
{{
    "protocol_titles": ["single title here"],
    "selection_reasoning": "why this single title was selected"
}}

If there are multiple equally important protocols:
{{
    "protocol_titles": ["first title", "second title", "etc"],
    "selection_reasoning": "why multiple titles were selected as equally important"
}}

If no protocol title is found:
{{
    "protocol_titles": [],
    "selection_reasoning": "why no titles were found"
}}

Guidelines:
- Include all titles that appear to be equally important or prominent
- If one protocol is clearly the main focus, return only that one
- Always return an array, even for single titles
- Use semantic understanding to determine which quoted text represents actual protocol titles
"""

# for eval_set_converter
EXTRACTION_PROMPT_TEMPLATE = """
You are an extraction expert. Your task is to identify and extract video uri
and protocol title from text responses.

Look for video uri that are typically:
- local paths in the initial user request
- Enclosed in quotes

Look for protocol title that are typically:
- in the last model or user responses
- Enclosed in quotes
- Mentioned after words like "protocol", "found", "titled", "called", etc.
- The main protocol being referenced in the response

Text to analyze: {response_text}

Extract the video uri and protocol title and return your response in the following
JSON format:

If there is a clear main protocol:
{{
    "video_uri": ["uri here"]
    "protocol_title": ["title here"],
    "selection_reasoning": "why this uri and title was selected"
}}

If no uri or protocol title is found:
{{
    "video_uri": [],
    "protocol_titles": [],
    "selection_reasoning": "why no uri or titles were found"
}}

Guidelines:
- Use semantic understanding to determine which quoted text represents the actual
uri and protocol title
"""
