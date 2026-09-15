"""LLM Provider implementations: Mock, Gemini, and OpenAI."""

import json
import re
from typing import Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.ai.base import LLMProvider


class MockProvider(LLMProvider):
    """Deterministic Mock AI Provider for reliable testing and offline development."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Produce structured JSON reasoning based on input context."""
        logger.info("MockProvider: Generating deterministic AI change plan.")

        # Extract detected changes mentioned in prompt if available
        changes = []

        # Parse detected diffs in prompt text
        if "POST /users" in prompt:
            if "email" in prompt:
                changes.append({
                    "type": "modified",
                    "method": "POST",
                    "path": "/users",
                    "summary": "Create User with required email",
                    "description": "User registration endpoint now requires an email address.",
                    "documentation_changes": {
                        "request_fields_added": [
                            {"name": "email", "type": "string", "required": True, "description": "User email"}
                        ],
                        "request_fields_removed": [],
                        "response_fields_added": [],
                        "response_fields_removed": [],
                        "path_parameters_added": [],
                        "path_parameters_removed": [],
                        "query_parameters_added": [],
                        "query_parameters_removed": []
                    },
                    "explanation": "The create-user request model was modified to require an email field.",
                    "impact": {
                        "severity": "HIGH",
                        "reason": "Existing clients calling POST /users must provide the new required email field."
                    },
                    "confidence": 0.96
                })
            else:
                changes.append({
                    "type": "added",
                    "method": "POST",
                    "path": "/users",
                    "summary": "Create new user",
                    "description": "Endpoint to register a new user in the system.",
                    "documentation_changes": {
                        "request_fields_added": [
                            {"name": "name", "type": "string", "required": True, "description": "User full name"}
                        ],
                        "request_fields_removed": [],
                        "response_fields_added": [],
                        "response_fields_removed": [],
                        "path_parameters_added": [],
                        "path_parameters_removed": [],
                        "query_parameters_added": [],
                        "query_parameters_removed": []
                    },
                    "explanation": "A new endpoint POST /users was introduced for creating user accounts.",
                    "impact": {
                        "severity": "LOW",
                        "reason": "Additive non-breaking endpoint."
                    },
                    "confidence": 0.98
                })

        if "GET /products" in prompt and ("removed" in prompt or "deleted" in prompt):
            changes.append({
                "type": "removed",
                "method": "GET",
                "path": "/products",
                "summary": "List products (Removed)",
                "description": "Endpoint has been removed.",
                "documentation_changes": {
                    "request_fields_added": [],
                    "request_fields_removed": [],
                    "response_fields_added": [],
                    "response_fields_removed": [],
                    "path_parameters_added": [],
                    "path_parameters_removed": [],
                    "query_parameters_added": [],
                    "query_parameters_removed": []
                },
                "explanation": "The GET /products route was removed from the backend codebase.",
                "impact": {
                    "severity": "HIGH",
                    "reason": "Clients relying on GET /products will receive 404 Not Found."
                },
                "confidence": 0.99
            })

        # Fallback if specific known pattern not matched: generate generic valid response
        if not changes:
            # Check for any method and path in prompt
            match = re.search(r"(GET|POST|PUT|DELETE|PATCH)\s+([/\w{}_\-]+)", prompt, re.IGNORECASE)
            method = match.group(1).upper() if match else "GET"
            path = match.group(2) if match else "/api/endpoint"
            
            changes.append({
                "type": "modified",
                "method": method,
                "path": path,
                "summary": f"Updated {method} {path}",
                "description": "API updated based on backend code changes.",
                "documentation_changes": {
                    "request_fields_added": [],
                    "request_fields_removed": [],
                    "response_fields_added": [],
                    "response_fields_removed": [],
                    "path_parameters_added": [],
                    "path_parameters_removed": [],
                    "query_parameters_added": [],
                    "query_parameters_removed": []
                },
                "explanation": f"Detected updates in backend source for {method} {path}.",
                "impact": {
                    "severity": "LOW",
                    "reason": "Standard non-breaking update."
                },
                "confidence": 0.92
            })

        return json.dumps({
            "changes": changes,
            "overall_summary": "Processed API updates from commit diff."
        })


class GeminiProvider(LLMProvider):
    """Google Gemini API Provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL or "gemini-2.5-flash"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            logger.warning("Gemini API key not configured. Falling back to MockProvider.")
            return await MockProvider().generate(prompt, system_prompt)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini API Error ({response.status_code}): {response.text}")

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidate generated by Gemini API.")
            return candidates[0]["content"]["parts"][0]["text"]


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL or "gpt-4o-mini"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            logger.warning("OpenAI API key not configured. Falling back to MockProvider.")
            return await MockProvider().generate(prompt, system_prompt)

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"OpenAI API Error ({response.status_code}): {response.text}")

            data = response.json()
            return data["choices"][0]["message"]["content"]


def get_ai_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Factory to retrieve configured AI Provider."""
    name = (provider_name or settings.LLM_PROVIDER or "mock").lower()
    if name == "gemini":
        return GeminiProvider()
    elif name == "openai":
        return OpenAIProvider()
    else:
        return MockProvider()
