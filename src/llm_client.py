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


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
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
        # Free-tier models in particular are prone to transient 429s (shared
        # rate-limit pools) - retry those (and 5xx/network errors) with
        # backoff instead of failing the whole request on the first hiccup.
        self.max_retries = max_retries

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
        import time as _time

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

        for attempt in range(self.max_retries + 1):
            is_last_attempt = attempt == self.max_retries
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as e:
                if is_last_attempt:
                    logger.error(f"LLM request failed: {e}")
                    raise
                wait = min(2**attempt, 10)
                logger.warning(
                    f"LLM request failed ({e}); retrying in {wait}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                _time.sleep(wait)
                continue

            if resp.status_code in RETRYABLE_STATUS_CODES and not is_last_attempt:
                wait = min(float(resp.headers.get("Retry-After", 2**attempt)), 10)
                logger.warning(
                    f"LLM request got HTTP {resp.status_code}; retrying in {wait:.1f}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                _time.sleep(wait)
                continue

            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"LLM HTTP error {e.response.status_code}: {e.response.text[:300]}"
                )
                raise
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

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
