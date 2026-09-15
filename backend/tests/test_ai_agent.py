"""Tests for AIAgent and Provider abstraction."""

import pytest
from app.services.ai.agent import AIAgent
from app.services.ai.base import LLMProvider
from app.services.ai.provider import MockProvider
from app.services.openapi.comparator import DetectedAPIChange


class FaultyProvider(LLMProvider):
    """Provider that returns invalid JSON to test retry and fallback."""
    def __init__(self, fail_count: int = 1):
        self.attempts = 0
        self.fail_count = fail_count

    async def generate(self, prompt: str, system_prompt=None) -> str:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            return "This is not JSON at all."
        return '{"changes": [], "overall_summary": "Recovered"}'


@pytest.mark.asyncio
async def test_ai_agent_with_mock_provider():
    """Test AI Agent reasoning over detected changes."""
    agent = AIAgent(provider=MockProvider())

    detected_change = DetectedAPIChange(
        change_type="modified",
        method="POST",
        path="/users",
        summary="Create User",
        diff_details={"reason": "Added email field to request"},
        default_severity="HIGH",
    )

    plan, metadata = await agent.analyze_changes(
        detected_changes=[detected_change],
        git_diff="+ email: str\n",
        existing_openapi=None,
    )

    assert plan is not None
    assert len(plan.changes) >= 1
    ch = plan.changes[0]
    assert ch.method == "POST"
    assert ch.path == "/users"
    assert ch.confidence >= 0.85
    assert metadata["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_ai_agent_retry_and_recovery():
    """Test AI Agent retries upon receiving malformed JSON."""
    provider = FaultyProvider(fail_count=1)
    agent = AIAgent(provider=provider)

    plan, metadata = await agent.analyze_changes(
        detected_changes=[],
        git_diff="",
        existing_openapi=None,
    )

    assert provider.attempts == 2
    assert plan is not None
    assert metadata["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_ai_agent_fallback_on_total_failure():
    """Test fallback plan when provider persistently fails."""
    provider = FaultyProvider(fail_count=5)
    agent = AIAgent(provider=provider)

    detected = [
        DetectedAPIChange(
            change_type="added",
            method="GET",
            path="/items",
            summary="List items",
            diff_details={"reason": "New endpoint"},
        )
    ]

    plan, metadata = await agent.analyze_changes(
        detected_changes=detected,
        git_diff="",
        existing_openapi=None,
    )

    assert plan is not None
    assert len(plan.changes) == 1
    assert plan.changes[0].path == "/items"
    assert metadata["status"] == "FAILED"
