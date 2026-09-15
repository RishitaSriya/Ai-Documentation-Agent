"""AI Agent for semantic reasoning over API code changes."""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from app.core.logging import logger, log_pipeline_event
from app.schemas.agent import APIChangePlan, SingleAPIChangePlan
from app.services.ai.base import LLMProvider
from app.services.ai.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, RETRY_PROMPT_TEMPLATE
from app.services.ai.provider import get_ai_provider
from app.services.openapi.comparator import DetectedAPIChange


class AIAgent:
    """Agent that reasons about semantic API changes and generates structured update plans."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_ai_provider()

    async def analyze_changes(
        self,
        detected_changes: List[DetectedAPIChange],
        git_diff: str,
        existing_openapi: Optional[Dict[str, Any]] = None
    ) -> Tuple[APIChangePlan, Dict[str, Any]]:
        """Analyze API changes and return structured APIChangePlan + run metadata."""
        log_pipeline_event("AI_AGENT", f"Reasoning over {len(detected_changes)} detected changes...")

        # 1. Format prompt context
        changes_json_str = json.dumps([c.to_dict() for c in detected_changes], indent=2)
        openapi_summary = self._summarize_openapi(existing_openapi)

        prompt = USER_PROMPT_TEMPLATE.format(
            detected_changes_json=changes_json_str,
            git_diff=git_diff[:4000] if git_diff else "No direct text diff available.",
            existing_openapi_summary=openapi_summary,
        )

        input_data = {
            "num_detected_changes": len(detected_changes),
            "diff_length": len(git_diff) if git_diff else 0,
            "has_existing_openapi": existing_openapi is not None,
        }

        # 2. Invoke LLM Provider
        raw_output = await self.provider.generate(prompt, system_prompt=SYSTEM_PROMPT)

        # 3. Attempt JSON parse and Pydantic validation
        parsed_plan, parse_error = self._parse_output(raw_output)

        if parsed_plan is None:
            logger.warning(f"First AI output validation failed: {parse_error}. Attempting retry with correction prompt...")
            retry_prompt = f"{prompt}\n\n" + RETRY_PROMPT_TEMPLATE.format(error_details=parse_error)
            raw_output = await self.provider.generate(retry_prompt, system_prompt=SYSTEM_PROMPT)
            parsed_plan, parse_error = self._parse_output(raw_output)

        if parsed_plan is None:
            logger.error(f"AI Agent failed after retry: {parse_error}")
            # Fallback: construct deterministic baseline plan from detected structural changes
            parsed_plan = self._build_deterministic_fallback_plan(detected_changes)
            status = "FAILED"
            error = f"AI output validation error: {parse_error}"
        else:
            status = "SUCCESS"
            error = None

        run_metadata = {
            "model": getattr(self.provider, "model", "mock"),
            "status": status,
            "error": error,
            "input_data": input_data,
            "output_data": parsed_plan.model_dump(),
        }

        return parsed_plan, run_metadata

    def _parse_output(self, raw_text: str) -> Tuple[Optional[APIChangePlan], Optional[str]]:
        """Extract JSON and validate against APIChangePlan Pydantic model."""
        try:
            # Strip markdown code fences if present
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)

            data = json.loads(cleaned)
            plan = APIChangePlan.model_validate(data)
            return plan, None
        except (json.JSONDecodeError, ValidationError) as e:
            return None, str(e)
        except Exception as e:
            return None, str(e)

    def _build_deterministic_fallback_plan(
        self, detected_changes: List[DetectedAPIChange]
    ) -> APIChangePlan:
        """Create reliable fallback plan directly from AST comparator results if AI fails."""
        plans: List[SingleAPIChangePlan] = []
        for c in detected_changes:
            doc_changes = {"request_fields_added": [], "request_fields_removed": []}
            if "request_body_diff" in c.diff_details:
                rf = c.diff_details["request_body_diff"]
                doc_changes["request_fields_added"] = rf.get("fields_added", [])
                doc_changes["request_fields_removed"] = rf.get("fields_removed", [])

            plans.append(
                SingleAPIChangePlan(
                    type=c.change_type,
                    method=c.method,
                    path=c.path,
                    summary=c.summary or f"{c.method.upper()} {c.path}",
                    explanation=c.diff_details.get("reason", f"API {c.change_type} detected from backend changes."),
                    documentation_changes=doc_changes,
                    impact={"severity": c.default_severity, "reason": "Evaluated based on deterministic API changes."},
                    confidence=0.90,
                )
            )

        return APIChangePlan(
            changes=plans,
            overall_summary="Deterministic fallback change plan applied."
        )

    def _summarize_openapi(self, openapi_dict: Optional[Dict[str, Any]]) -> str:
        if not openapi_dict:
            return "No previous OpenAPI specification found."

        paths = openapi_dict.get("paths", {})
        endpoints_summary = []
        for path_str, path_obj in list(paths.items())[:15]:
            if isinstance(path_obj, dict):
                for method, op in path_obj.items():
                    if isinstance(op, dict):
                        endpoints_summary.append(f"- {method.upper()} {path_str}: {op.get('summary', '')}")

        return f"Existing Endpoints ({len(endpoints_summary)} shown):\n" + "\n".join(endpoints_summary)
