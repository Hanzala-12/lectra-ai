"""
LLM Client — provider abstraction for the NLP/LLM half of the system
(notes, quiz, schedule, evaluation, RAG chat).

Default provider: OpenRouter (OpenAI-compatible chat completions API).
The primary API key is read from the environment (OPENROUTER_API_KEY) and can
be added later — until then `is_configured()` returns False and callers
return a clean "LLM not configured" response instead of crashing.

Optional fallback keys (OPENROUTER_API_KEY_2, _3, ...) let the client rotate
to a different account automatically when one is out of credits (402) or
invalid (401), or when a rate limit (429) persists through the existing
retry-with-backoff on the current key — instead of failing the whole
request just because one specific key/account is temporarily unusable.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class LLMNotConfigured(Exception):
    """Raised when an LLM call is attempted without an API key."""


# Transient — worth retrying the SAME key with backoff first.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
# Key/account-specific — retrying the same key is pointless, move on to the
# next configured key immediately (no backoff wasted on a key that's simply
# out of credits or revoked).
KEY_ROTATE_STATUS_CODES = {401, 402}


def _collect_api_keys(explicit: Optional[str]) -> List[str]:
    """Primary key first (explicit arg, then OPENROUTER_API_KEY / LLM_API_KEY),
    followed by any OPENROUTER_API_KEY_2.. OPENROUTER_API_KEY_9 fallbacks that
    are set. Order is the rotation order. Duplicates removed, empties dropped.

    An explicit `explicit` arg (as tests pass, e.g. api_key="fake-key") is
    authoritative and used alone, with NO env-based fallback collection -
    mirrors how the single-key version worked (explicit overrides env
    entirely) and keeps tests isolated from whatever real fallback keys
    happen to be sitting in a loaded .env (backend.py's load_dotenv() runs
    at import time, before any test gets a chance to construct a client).
    """
    if explicit:
        return [explicit]
    keys = []
    primary = os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")
    if primary:
        keys.append(primary)
    for i in range(2, 10):
        extra = os.getenv(f"OPENROUTER_API_KEY_{i}")
        if extra:
            keys.append(extra)
    # de-dupe while preserving order (a key pasted into both slots shouldn't
    # be tried twice)
    seen = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        # Read provider settings from env so the key(s) can be dropped in later.
        self.api_keys = _collect_api_keys(api_key)
        # Kept for backwards compatibility (is_configured(), anything reading
        # .api_key directly) — always the first/primary key.
        self.api_key = self.api_keys[0] if self.api_keys else None
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
        return bool(self.api_keys)

    # -----------------------------------------------------------------
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> str:
        """Send a chat-completion request and return the assistant text.
        Rotates across every configured API key before giving up."""
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

        last_error: Optional[BaseException] = None

        for key_index, api_key in enumerate(self.api_keys):
            is_last_key = key_index == len(self.api_keys) - 1
            headers = {
                "Authorization": f"Bearer {api_key}",
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
                    last_error = e
                    if is_last_attempt:
                        break  # exhausted retries on this key -> try next key
                    wait = min(2**attempt, 10)
                    logger.warning(
                        f"LLM request failed ({e}); retrying in {wait}s "
                        f"(key {key_index + 1}/{len(self.api_keys)}, "
                        f"attempt {attempt + 1}/{self.max_retries})"
                    )
                    _time.sleep(wait)
                    continue

                if resp.status_code in KEY_ROTATE_STATUS_CODES:
                    last_error = httpx.HTTPStatusError(
                        f"key {key_index + 1} rejected: HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    if not is_last_key:
                        logger.warning(
                            f"LLM key {key_index + 1}/{len(self.api_keys)} got "
                            f"HTTP {resp.status_code} (out of credits or invalid) "
                            f"- rotating to the next key"
                        )
                    break  # no point retrying the same key on 401/402

                if resp.status_code in RETRYABLE_STATUS_CODES and not is_last_attempt:
                    wait = min(float(resp.headers.get("Retry-After", 2**attempt)), 10)
                    logger.warning(
                        f"LLM request got HTTP {resp.status_code}; retrying in "
                        f"{wait:.1f}s (key {key_index + 1}/{len(self.api_keys)}, "
                        f"attempt {attempt + 1}/{self.max_retries})"
                    )
                    _time.sleep(wait)
                    continue

                if resp.status_code in RETRYABLE_STATUS_CODES and is_last_attempt:
                    # Retries exhausted on this key too - worth trying the next
                    # key in case it has separate rate-limit headroom, rather
                    # than failing outright.
                    last_error = httpx.HTTPStatusError(
                        f"key {key_index + 1} exhausted retries: HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    break

                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    # A genuine, non-transient, non-auth client error (bad
                    # request, etc.) - rotating keys wouldn't fix this and
                    # would just mask the real problem. Fail immediately.
                    logger.error(
                        f"LLM HTTP error {e.response.status_code}: {e.response.text[:300]}"
                    )
                    raise
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()

            # Reaching here means this key's attempts are exhausted (network
            # error, 401/402, or a persistent retryable status) - loop
            # continues to the next key, if any.

        # Every configured key failed.
        if last_error:
            logger.error(
                f"LLM request failed on all {len(self.api_keys)} configured key(s)"
            )
            raise last_error
        raise RuntimeError("LLM request failed on all configured keys")

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ):
        """Like chat(), but yields text deltas as they arrive instead of
        returning the full response at once.

        Key rotation applies only to a rejected *connection* (401/402, or a
        network error before any bytes came back) — safe to silently retry
        the next key at that point since nothing has reached the caller yet.
        Once a key's stream has actually started, a later failure raises
        instead of silently retrying, since some content may already have
        been yielded (and, for a chat/notes caller, already shown to a
        person) — a transparent retry there would risk duplicated or
        contradictory partial output.
        """
        if not self.is_configured():
            raise LLMNotConfigured(
                "LLM is not configured. Add OPENROUTER_API_KEY to your .env file."
            )

        import httpx
        import json as _json

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        last_error: Optional[BaseException] = None

        for key_index, api_key in enumerate(self.api_keys):
            is_last_key = key_index == len(self.api_keys) - 1
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("APP_URL", "http://localhost"),
                "X-Title": "Lectra AI",
            }
            started = False
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as resp:
                        if resp.status_code in KEY_ROTATE_STATUS_CODES or (
                            resp.status_code in RETRYABLE_STATUS_CODES
                        ):
                            resp.read()  # drain so httpx doesn't warn on a closed stream
                            last_error = httpx.HTTPStatusError(
                                f"key {key_index + 1} rejected: HTTP {resp.status_code}",
                                request=resp.request,
                                response=resp,
                            )
                            if not is_last_key:
                                logger.warning(
                                    f"LLM stream key {key_index + 1}/{len(self.api_keys)} got "
                                    f"HTTP {resp.status_code} before any content — rotating"
                                )
                            continue
                        resp.raise_for_status()
                        started = True
                        for line in resp.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data = line[len("data: ") :]
                            if data.strip() == "[DONE]":
                                return
                            chunk = _json.loads(data)
                            delta = (
                                chunk.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content")
                            )
                            if delta:
                                yield delta
                        return
            except (httpx.TimeoutException, httpx.TransportError) as e:
                if started:
                    raise
                last_error = e
                continue

        if last_error:
            logger.error(
                f"LLM stream failed on all {len(self.api_keys)} configured key(s)"
            )
            raise last_error
        raise RuntimeError("LLM stream failed on all configured keys")

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
