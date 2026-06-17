"""
LLM Client — provider abstraction for the NLP/LLM half of the system
(notes, quiz, schedule, evaluation, RAG chat).

Default provider: OpenRouter (OpenAI-compatible chat completions API).
The API key is read from the environment (OPENROUTER_API_KEY) and can be added
later — until then `is_configured()` returns False and callers return a clean
"LLM not configured" response instead of crashing.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class LLMNotConfigured(Exception):
    """Raised when an LLM call is attempted without an API key."""


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        # Read provider settings from env so the key can be dropped in later.
        self.api_key = (
            api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")
        )
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        # A small, capable, inexpensive default; override via env if desired.
        self.model = model or os.getenv("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key)

    # -----------------------------------------------------------------
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> str:
        """Send a chat-completion request and return the assistant text."""
        if not self.is_configured():
            raise LLMNotConfigured(
                "LLM is not configured. Add OPENROUTER_API_KEY to your .env file."
            )

        import httpx

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter optional attribution headers
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost"),
            "X-Title": "Lectra AI",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"LLM HTTP error {e.response.status_code}: {e.response.text[:300]}"
            )
            raise
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def complete(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def complete_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Any:
        """Ask for JSON and parse it robustly (handles code-fences / stray text)."""
        kwargs.setdefault("json_mode", True)
        kwargs.setdefault("temperature", 0.2)
        raw = self.complete(prompt, system=system, **kwargs)
        return _extract_json(raw)


def _extract_json(text: str) -> Any:
    """Best-effort JSON extraction from an LLM response."""
    text = text.strip()
    # strip ```json ... ``` fences
    if text.startswith("```"):
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # find the first {...} or [...] block
        for open_c, close_c in (("{", "}"), ("[", "]")):
            start = text.find(open_c)
            end = text.rfind(close_c)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")


# Module-level singleton (cheap; no network until a call is made)
_default_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
