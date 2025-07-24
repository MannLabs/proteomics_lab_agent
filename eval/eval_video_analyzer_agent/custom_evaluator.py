"""Evaluation for video analyzer. Protocol title extraction and ROUGE comparison evaluator."""

from __future__ import annotations

import inspect
import json
import logging
import re
from typing import TYPE_CHECKING, Callable

from google import genai
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.eval_metrics import EvalMetric, JudgeModelOptions
from google.adk.evaluation.evaluator import (
    EvaluationResult,
    Evaluator,
    PerInvocationResult,
)
from google.adk.evaluation.llm_as_judge_utils import (
    get_eval_status,
    get_text_from_content,
)
from google.adk.evaluation.metric_evaluator_registry import (
    DEFAULT_METRIC_EVALUATOR_REGISTRY,
)
from pydantic import BaseModel
from rouge_score import rouge_scorer
from typing_extensions import override

if TYPE_CHECKING:
    from google.adk.evaluation.eval_case import Invocation
    from google.adk.evaluation.eval_set import EvalSet

logger = logging.getLogger(__name__)

EVAL_MODEL = "gemini-2.5-flash"


class ProtocolTitleExtractor:
    """Utility class to extract protocol titles from LLM responses using semantic understanding."""

    def __init__(self, extraction_model: str) -> None:
        """Initialize the protocol title extractor with an LLM model and prompt."""
        self.extraction_model = extraction_model
        self._extraction_prompt_template = """
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
            - If the response mentions multiple protocols but discusses them all equally, return all of them
            - Always return an array, even for single titles
            - Use semantic understanding to determine which quoted text represents actual protocol titles
        """

    async def extract_protocol_title(
        self,
        response_text: str,
    ) -> str | list[str]:
        """Extract protocol title(s) from LLM response using semantic analysis.

        Uses an LLM to extract protocol titles from response text with structured
        output parsing. Falls back to regex extraction if LLM extraction fails.

        Parameters
        ----------
        response_text : str
            The full LLM response text to extract protocol titles from

        Returns
        -------
        str | list[str]
            Single protocol title, list of protocol titles, or None if not found

        """
        if not response_text:
            return None

        try:
            prompt = self._extraction_prompt_template.format(
                response_text=response_text
            )

            class ProtocolTitles(BaseModel):
                protocol_titles: list[str]
                selection_reasoning: str

            client = genai.Client()
            response = client.models.generate_content(
                model=self.extraction_model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": list[ProtocolTitles],
                },
            )

            parsed_protocols: list[ProtocolTitles] = response.parsed

            if parsed_protocols and len(parsed_protocols) > 0:
                protocol_titles_obj = parsed_protocols[0]
                return protocol_titles_obj.protocol_titles

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.info(
                f"Could not extract valid titles from parsed response - caused Exception in LLM extraction: {e}"
            )
            logger.info("Falling back to regex extraction")
            return self._enhanced_regex_extraction(response_text)

    def _enhanced_regex_extraction(self, response_text: str) -> str | list[str]:
        """Extract protocol title(s) from LLM response using regex."""
        if not response_text:
            return None

        double_quote_pattern = r'"([^"]+)"'
        double_matches = re.findall(double_quote_pattern, response_text)

        single_quote_pattern = r"'([^']+)'"
        single_matches = re.findall(single_quote_pattern, response_text)

        all_matches = double_matches + single_matches
        return all_matches if all_matches else None


class ProtocolTitleRougeEvaluator(Evaluator):
    """Evaluator that extracts protocol titles and compares them using ROUGE."""

    def __init__(self, eval_metric: EvalMetric) -> None:
        """Initialize the evaluator with metric configuration and scoring tools.

        Sets up the protocol title extractor with the appropriate judge model
        and initializes ROUGE-1 scorer for unigram overlap evaluation.

        Parameters
        ----------
        eval_metric : EvalMetric
            Evaluation metric configuration is extracted from test_config.json file and contains judge model options
            and other evaluation parameters
            Example test_config.json file:
            {
            "criteria": {
                "protocol_title_rouge_evaluation": {
                "threshold": 0.7,
                "judge_model_options": {
                    "judge_model": "gemini-2.5-flash",
                    "judge_model_config": {
                    "temperature": 0.1
                    }
                }
                }
            }
            }

        Returns
        -------
        None

        """
        self._eval_metric = eval_metric

        judge_model = EVAL_MODEL
        if (
            eval_metric.judge_model_options
            and eval_metric.judge_model_options.judge_model
        ):
            judge_model = eval_metric.judge_model_options.judge_model
        self.extractor = ProtocolTitleExtractor(judge_model)

        # ROUGE-1: Unigram (single word) overlap
        self.rouge_scorer = rouge_scorer.RougeScorer(["rouge1"], use_stemmer=True)

    def _calculate_rouge_score(
        self, candidate: str | list[str], reference: str | list[str]
    ) -> float:
        """Calculate ROUGE-1 F-measure between candidate and reference. It can handle multiple titles.

        Strategy: Calculate ROUGE between each candidate and reference pair, return best score.
        """
        candidate_list = (
            candidate
            if isinstance(candidate, list)
            else [candidate]
            if candidate
            else []
        )
        reference_list = (
            reference
            if isinstance(reference, list)
            else [reference]
            if reference
            else []
        )

        if not candidate_list or not reference_list:
            return 0.0

        max_rouge_score = 0.0

        for cand in candidate_list:
            for ref in reference_list:
                if cand and ref:
                    scores = self.rouge_scorer.score(ref, cand)
                    rouge_score = scores["rouge1"].fmeasure
                    max_rouge_score = max(max_rouge_score, rouge_score)

        return max_rouge_score

    def _get_expected_protocol_title(
        self, expected_invocation: Invocation
    ) -> str | list[str] | None:
        """Extract expected protocol title(s) from the expected invocation.

        Requirment: Multiple titles must be a comma separated list in the evalset.json file.
        This should serve as a reference/golden response.
        """
        reference_text = get_text_from_content(expected_invocation.final_response)
        if not reference_text:
            return None

        reference_text = reference_text.strip()

        if "," in reference_text:
            titles = [title.strip().strip("\"'") for title in reference_text.split(",")]
            return [title for title in titles if title]

        return reference_text

    @override
    async def evaluate_invocations(
        self,
        actual_invocations: list[Invocation],
        expected_invocations: list[Invocation],
    ) -> EvaluationResult:
        """Evaluate accuracy for extracting protocol title from video using LLM-based extraction and ROUGE scoring.

        Extracts protocol titles from actual invocation responses (agent response) using LLM semantic analysis
        (with regex fallback) and compares them against expected titles using ROUGE-1 F-measure.
        Processes each invocation pair, calculates individual ROUGE scores, and aggregates
        results into an overall evaluation with pass/fail status based on configured threshold.

        Parameters
        ----------
        actual_invocations : list[Invocation]
            List of actual invocations containing response text to extract protocol titles from
        expected_invocations : list[Invocation]
            List of expected invocations containing ground truth protocol titles for comparison

        Returns
        -------
        EvaluationResult
            Evaluation result containing:
            - overall_score: Average ROUGE-1 F-measure across all invocation pairs
            - overall_eval_status: Pass/fail status based on threshold comparison
            - per_invocation_results: Individual results for each invocation pair with
            extracted titles, expected titles, ROUGE scores, and evaluation status

        """
        total_score = 0.0
        num_invocations = 0
        per_invocation_results = []

        logger.info("=" * 80)
        logger.info("LLM-BASED PROTOCOL TITLE EXTRACTION & ROUGE EVALUATION")
        logger.info("=" * 80)

        for actual, expected in zip(actual_invocations, expected_invocations):
            response_text = get_text_from_content(actual.final_response) or ""
            extracted_title = await self.extractor.extract_protocol_title(response_text)
            expected_title = self._get_expected_protocol_title(expected)

            logger.info("-" * 80)
            logger.info(f"Full Response: {response_text}")
            logger.info(
                f"Extracted Title(s): {self._format_titles_for_display(extracted_title)}"
            )
            logger.info(
                f"Expected Title(s): {self._format_titles_for_display(expected_title)}"
            )

            if extracted_title and expected_title:
                rouge_score = self._calculate_rouge_score(
                    extracted_title, expected_title
                )
                logger.info(f"ROUGE-1 F-measure: {rouge_score:.4f}")
            elif not extracted_title and not expected_title:
                rouge_score = 0.0
                logger.info(f"Both titles are None/empty - No match: {rouge_score:.4f}")
            elif not extracted_title:
                rouge_score = 0.0
                logger.warning(
                    f"Failed to extract protocol title - Score: {rouge_score:.4f}"
                )
            elif not expected_title:
                rouge_score = 0.0
                logger.warning(
                    f"Expected no title but extracted {self._format_titles_for_display(extracted_title)} - Score: {rouge_score:.4f}"
                )

            eval_status = get_eval_status(rouge_score, self._eval_metric.threshold)
            per_invocation_results.append(
                PerInvocationResult(
                    actual_invocation=actual,
                    expected_invocation=expected,
                    score=rouge_score,
                    eval_status=eval_status,
                )
            )
            total_score += rouge_score
            num_invocations += 1

        if per_invocation_results:
            overall_score = total_score / num_invocations
            overall_status = get_eval_status(overall_score, self._eval_metric.threshold)

            logger.info("=" * 80)
            logger.info("FINAL RESULTS")
            logger.info(f"Overall Actual Score: {overall_score:.4f}")
            logger.info(f"Required Score / Threshold: {self._eval_metric.threshold}")
            logger.info(f"Status: {overall_status.name}")
            logger.info("=" * 80)

            return EvaluationResult(
                overall_score=overall_score,
                overall_eval_status=overall_status,
                per_invocation_results=per_invocation_results,
            )

        return EvaluationResult()

    def _format_titles_for_display(self, titles: str | list[str]) -> str:
        """Format titles for display in console output."""
        if not titles:
            return "'None'"
        if isinstance(titles, str):
            return f"'{titles}'"
        if isinstance(titles, list):
            if len(titles) == 1:
                return f"'{titles[0]}'"
            formatted_titles = "', '".join(titles)
            return f"['{formatted_titles}']"
        return str(titles)


def register_protocol_title_evaluator() -> None:
    """Register the custom protocol title extraction & ROUGE evaluator & modified eval set."""
    DEFAULT_METRIC_EVALUATOR_REGISTRY.register_evaluator(
        metric_name="protocol_title_rouge_evaluation",
        evaluator=ProtocolTitleRougeEvaluator,
    )

    _original_get_metric_evaluator = AgentEvaluator._get_metric_evaluator  # noqa: SLF001 (privat member accessed)
    _original_evaluate_eval_set = AgentEvaluator.evaluate_eval_set

    def wrapped_get_metric_evaluator(
        metric_name: str, threshold: float | dict
    ) -> Evaluator:
        """Wrapper that injects the original method into the patched implementation."""
        return _patched_get_metric_evaluator(
            metric_name, threshold, _original_get_metric_evaluator
        )

    AgentEvaluator._get_metric_evaluator = wrapped_get_metric_evaluator  # noqa: SLF001
    AgentEvaluator.evaluate_eval_set = _patched_evaluate_eval_set


@staticmethod
def _patched_get_metric_evaluator(
    metric_name: str,
    threshold: float | dict,
    _original_get_metric_evaluator: Callable[[str, float | dict], Evaluator],
) -> Evaluator:
    """Get metric evaluator with support for both ADK and enhanced configuration formats.

    Enhanced version that supports backward compatibility between old threshold-only
    configurations (float) implemented in ADK and new dictionary-based configurations that include
    judge model options and other advanced settings. Attempts to create an evaluator
    with the new registry system and falls back to the original implementation
    if creation fails.

    Parameters
    ----------
    metric_name : str
        Name of the evaluation metric to create an evaluator for
    threshold : Union[float, dict]
        Evaluation threshold configuration. Can be either:
        - float: Simple threshold value (ADK format)
        - dict: Enhanced configuration containing 'threshold' key and optional
        'judge_model_options' with 'judge_model' and 'judge_model_config'
    original_get_metric_evaluator : Callable
        Reference to the original unpatched method for fallback behavior

    Returns
    -------
    Evaluator
        Configured evaluator instance for the specified metric

    Raises
    ------
    ValueError
        If threshold is a dict but missing required 'threshold' key

    """
    if isinstance(threshold, dict):
        if "threshold" not in threshold:
            raise ValueError(f"Missing 'threshold' in config for metric {metric_name}")

        judge_model_options = None
        if "judge_model_options" in threshold:
            judge_options_dict = threshold["judge_model_options"]
            judge_model_options = JudgeModelOptions(
                judge_model=judge_options_dict.get("judge_model"),
                judge_model_config=judge_options_dict.get("judge_model_config"),
            )

        eval_metric = EvalMetric(
            metric_name=metric_name,
            threshold=threshold["threshold"],
            judge_model_options=judge_model_options,
        )

        try:
            return DEFAULT_METRIC_EVALUATOR_REGISTRY.get_evaluator(eval_metric)
        except (KeyError, ValueError, AttributeError) as e:
            logger.debug(
                f"Failed to get evaluator from registry for {metric_name}: {e}"
            )

    return _original_get_metric_evaluator(metric_name, threshold)


@staticmethod
async def _patched_evaluate_eval_set(
    agent_module: str,
    eval_set: EvalSet,
    criteria: dict,
    num_runs: int = 1,
    agent_name: str | None = None,
) -> None:
    """Evaluate agent performance against evaluation set with enhanced async support.

    Enhanced version that properly handles asynchronous metric evaluators, particularly
    those using LLM-based extraction like the protocol title evaluator . Generates
    agent responses for the evaluation set, runs all specified metric evaluations,
    and raises AssertionError if any metrics fail to meet their thresholds. Supports
    both synchronous and asynchronous metric evaluators with automatic detection.

    Parameters
    ----------
    agent_module : str
        Module path to the agent implementation to be evaluated
    eval_set : EvalSet
        Evaluation dataset containing test cases and expected responses
    criteria : dict
        Dictionary mapping metric names to threshold configurations.
        Each threshold can be either a float (legacy) or dict (enhanced config)
    num_runs : int, default 1
        Number of times to run each evaluation case for statistical reliability
    agent_name : str, optional
        Name of the agent for identification in evaluation results

    Returns
    -------
    None
        Function completes successfully if all metrics pass thresholds

    Raises
    ------
    ModuleNotFoundError
        If required evaluation dependencies are not available
    AssertionError
        If any metric evaluation fails to meet its threshold requirement.
        Error message includes summary of all failed metrics with scores.

    """
    try:
        from google.adk.evaluation.evaluation_generator import EvaluationGenerator
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError("Missing eval dependencies") from e

    eval_case_responses_list = await EvaluationGenerator.generate_responses(
        eval_set=eval_set,
        agent_module_path=agent_module,
        repeat_num=num_runs,
        agent_name=agent_name,
    )

    failures = []
    for eval_case_responses in eval_case_responses_list:
        actual_invocations = [
            invocation
            for invocations in eval_case_responses.responses
            for invocation in invocations
        ]
        expected_invocations = eval_case_responses.eval_case.conversation * num_runs

        for metric_name, threshold in criteria.items():
            metric_evaluator = AgentEvaluator._get_metric_evaluator(  # noqa: SLF001
                metric_name=metric_name, threshold=threshold
            )

            # delay caused by LLM title extraction requires await to aviod run time errors
            if inspect.iscoroutinefunction(metric_evaluator.evaluate_invocations):
                evaluation_result = await metric_evaluator.evaluate_invocations(
                    actual_invocations=actual_invocations,
                    expected_invocations=expected_invocations,
                )
            else:
                evaluation_result = metric_evaluator.evaluate_invocations(
                    actual_invocations=actual_invocations,
                    expected_invocations=expected_invocations,
                )

            if evaluation_result.overall_eval_status.name != "PASSED":
                failures.append(
                    f"{metric_name} failed: {evaluation_result.overall_score:.3f} < {threshold}"
                )

    if failures:
        raise AssertionError(f"Evaluation failed. Summary: {'; '.join(failures)}")
