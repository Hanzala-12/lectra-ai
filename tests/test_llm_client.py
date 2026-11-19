"""
LLM client retry-with-backoff tests. Mocks httpx entirely - no real network
calls, no credits needed, fast.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import httpx
import pytest

from llm_client import LLMClient


def _fake_response(status_code, content="Hello", headers=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def client():
    return LLMClient(api_key="fake-key", max_retries=2)


def test_success_on_first_try_no_retry(client):
    ok = _fake_response(200, "real answer")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = ok
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "real answer"
    assert mock_httpx_client.__enter__.return_value.post.call_count == 1


def test_retries_on_429_then_succeeds(client, monkeypatch):
    rate_limited = _fake_response(429, headers={"Retry-After": "0"})
    ok = _fake_response(200, "worked on retry")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [rate_limited, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)  # don't actually wait in tests
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked on retry"
    assert mock_httpx_client.__enter__.return_value.post.call_count == 2


def test_gives_up_after_max_retries(client, monkeypatch):
    always_limited = _fake_response(429, headers={"Retry-After": "0"})
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = always_limited
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        with pytest.raises(httpx.HTTPStatusError):
            client.chat([{"role": "user", "content": "hi"}])
    # max_retries=2 -> 3 total attempts (1 initial + 2 retries)
    assert mock_httpx_client.__enter__.return_value.post.call_count == 3


def test_does_not_retry_on_non_retryable_4xx(client, monkeypatch):
    bad_request = _fake_response(400)
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = bad_request
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        with pytest.raises(httpx.HTTPStatusError):
            client.chat([{"role": "user", "content": "hi"}])
    assert mock_httpx_client.__enter__.return_value.post.call_count == 1


def test_retries_on_network_timeout(client, monkeypatch):
    ok = _fake_response(200, "worked after timeout")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [
        httpx.TimeoutException("timed out"),
        ok,
    ]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked after timeout"


# ----------------------------------------------------------------- multi-key rotation
# An explicit api_key= (single string) is authoritative with no env fallback
# collection (see _collect_api_keys) - these tests construct via env vars
# instead, the real path a multi-key .env goes through.


@pytest.fixture
def two_key_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "fake-key-2")
    monkeypatch.delenv("OPENROUTER_API_KEY_3", raising=False)
    return LLMClient(max_retries=1)


def test_collects_multiple_keys_from_env(two_key_client):
    assert two_key_client.api_keys == ["fake-key-1", "fake-key-2"]
    assert two_key_client.api_key == "fake-key-1"  # back-compat single-key accessor


def test_explicit_api_key_ignores_env_fallbacks(monkeypatch):
    # Guards against the real bug this session hit: backend.py's
    # load_dotenv() means a real multi-key .env is already loaded into the
    # process by the time a test constructs LLMClient(api_key="fake-key") -
    # an explicit key must NOT pick up unrelated real fallback keys from env.
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "some-real-key-that-should-be-ignored")
    client = LLMClient(api_key="fake-key")
    assert client.api_keys == ["fake-key"]


def test_rotates_to_next_key_on_402(two_key_client, monkeypatch):
    out_of_credits = _fake_response(402)
    ok = _fake_response(200, "worked on second key")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [out_of_credits, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = two_key_client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked on second key"
    # 402 rotates immediately - no wasted retry on the same (exhausted) key
    assert mock_httpx_client.__enter__.return_value.post.call_count == 2
    calls = mock_httpx_client.__enter__.return_value.post.call_args_list
    assert calls[0].kwargs["headers"]["Authorization"] == "Bearer fake-key-1"
    assert calls[1].kwargs["headers"]["Authorization"] == "Bearer fake-key-2"


def test_rotates_to_next_key_on_401(two_key_client, monkeypatch):
    invalid_key = _fake_response(401)
    ok = _fake_response(200, "worked on second key")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [invalid_key, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = two_key_client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked on second key"


def test_rotates_to_next_key_after_exhausting_retries_on_first(
    two_key_client, monkeypatch
):
    # two_key_client has max_retries=1 -> 2 attempts per key before rotating
    always_limited = _fake_response(429, headers={"Retry-After": "0"})
    ok = _fake_response(200, "worked on second key")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [
        always_limited,
        always_limited,
        ok,
    ]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = two_key_client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked on second key"
    assert mock_httpx_client.__enter__.return_value.post.call_count == 3


def test_raises_after_all_keys_exhausted(two_key_client, monkeypatch):
    always_limited = _fake_response(429, headers={"Retry-After": "0"})
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = always_limited
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        with pytest.raises(httpx.HTTPStatusError):
            two_key_client.chat([{"role": "user", "content": "hi"}])
    # 2 keys x 2 attempts each (max_retries=1) = 4 total calls
    assert mock_httpx_client.__enter__.return_value.post.call_count == 4


def test_does_not_rotate_keys_on_non_retryable_4xx(two_key_client, monkeypatch):
    # A genuine bad request isn't a key problem - rotating would just mask it.
    bad_request = _fake_response(400)
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = bad_request
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        with pytest.raises(httpx.HTTPStatusError):
            two_key_client.chat([{"role": "user", "content": "hi"}])
    assert mock_httpx_client.__enter__.return_value.post.call_count == 1


# ----------------------------------------------------------------- per-key models
# Real bug this guards against: OPENROUTER_MODEL used to be one value shared
# by every key, so a model-level failure (discontinued/404, or the empty-
# choices case below) took out every fallback key at once - rotating keys
# was useless since they all hit the same broken model. Confirmed live this
# session: minimax/minimax-m3:free got discontinued by OpenRouter (404 on
# every key), then separately a different model occasionally returned HTTP
# 200 with no usable content.


def test_different_keys_use_their_own_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "fake-key-2")
    monkeypatch.delenv(
        "OPENROUTER_API_KEY_3", raising=False
    )  # don't leak the real .env's 3rd key
    monkeypatch.setenv("OPENROUTER_MODEL", "model-one")
    monkeypatch.setenv("OPENROUTER_MODEL_2", "model-two")
    client = LLMClient(max_retries=1)
    assert client.key_models == ["model-one", "model-two"]

    # Rotate off key 1 (402 = out of credits) and confirm each request was
    # actually sent with ITS OWN key's model, not one shared value.
    ok = _fake_response(200, "worked on second key")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [
        _fake_response(402),  # rotate off key 1 without touching its model
        ok,
    ]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked on second key"
    calls = mock_httpx_client.__enter__.return_value.post.call_args_list
    assert calls[0].kwargs["json"]["model"] == "model-one"
    assert calls[1].kwargs["json"]["model"] == "model-two"


def test_discontinued_model_404_rotates_to_next_key_and_its_model(monkeypatch):
    """A retired primary model (HTTP 404) must fail over to key 2 / model 2
    instead of surfacing as a failed request (found by QA: the .env's retired
    primary model broke every LLM feature despite two working fallbacks)."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "fake-key-2")
    monkeypatch.delenv("OPENROUTER_API_KEY_3", raising=False)
    monkeypatch.setenv("OPENROUTER_MODEL", "retired-model")
    monkeypatch.setenv("OPENROUTER_MODEL_2", "live-model")
    client = LLMClient(max_retries=1)

    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [
        _fake_response(404),
        _fake_response(200, "answered by the fallback"),
    ]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "answered by the fallback"
    calls = mock_httpx_client.__enter__.return_value.post.call_args_list
    assert [c.kwargs["json"]["model"] for c in calls] == ["retired-model", "live-model"]


def test_per_key_model_falls_back_to_shared_default(monkeypatch):
    # Only OPENROUTER_MODEL set (no per-key overrides) - every key must use
    # it, exactly like before this feature existed.
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "fake-key-2")
    monkeypatch.setenv("OPENROUTER_API_KEY_3", "fake-key-3")
    monkeypatch.setenv("OPENROUTER_MODEL", "shared-model")
    monkeypatch.delenv("OPENROUTER_MODEL_2", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL_3", raising=False)
    client = LLMClient(max_retries=1)
    assert client.key_models == ["shared-model", "shared-model", "shared-model"]


def test_explicit_model_arg_overrides_every_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL_2", "should-be-ignored")
    client = LLMClient(api_key="fake-key", model="explicit-model")
    assert client.key_models == ["explicit-model"]


# ----------------------------------------------------------------- malformed response
# Real bug this guards against: a 200 status with an empty/missing choices
# list used to crash with an unhandled IndexError/KeyError instead of being
# treated as a retryable failure - confirmed live this session.


def test_empty_choices_retries_then_succeeds(client, monkeypatch):
    empty_choices = _fake_response(200)
    empty_choices.json.return_value = {"choices": []}
    ok = _fake_response(200, "real answer")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [empty_choices, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "real answer"
    assert mock_httpx_client.__enter__.return_value.post.call_count == 2


def test_missing_message_content_is_handled_not_crashed(client, monkeypatch):
    no_content = _fake_response(200)
    no_content.json.return_value = {"choices": [{"message": {}}]}
    ok = _fake_response(200, "real answer")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [no_content, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat([{"role": "user", "content": "hi"}])
    assert answer == "real answer"


def test_empty_choices_rotates_to_next_key_after_exhausting_retries(
    two_key_client, monkeypatch
):
    always_empty = _fake_response(200)
    always_empty.json.return_value = {"choices": []}
    ok = _fake_response(200, "worked on second key")
    mock_httpx_client = MagicMock()
    # two_key_client has max_retries=1 -> 2 attempts per key before rotating
    mock_httpx_client.__enter__.return_value.post.side_effect = [
        always_empty,
        always_empty,
        ok,
    ]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = two_key_client.chat([{"role": "user", "content": "hi"}])
    assert answer == "worked on second key"
    assert mock_httpx_client.__enter__.return_value.post.call_count == 3


def test_raises_after_all_keys_exhausted_on_empty_choices(client, monkeypatch):
    always_empty = _fake_response(200)
    always_empty.json.return_value = {"choices": []}
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = always_empty
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        with pytest.raises(ValueError, match="no usable content"):
            client.chat([{"role": "user", "content": "hi"}])


# ----------------------------------------------------------------- content_ok / complete_json
# Real bug this guards against: json_mode can get HTTP 200 with real, non-
# empty content that still doesn't parse as JSON (a free-tier model
# occasionally malforming its own JSON-mode output under load - seen live
# this session). Before content_ok existed, complete_json() called chat()
# ONCE, got that unparseable text back, and failed outright with no way to
# retry or rotate to a different key/model - the empty-choices handling
# above didn't catch this since the content itself was non-empty.


def test_chat_rejects_content_that_fails_the_validator(client, monkeypatch):
    bad_json = _fake_response(200, "not valid json {{{")
    ok = _fake_response(200, '{"answer": 42}')
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [bad_json, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        answer = client.chat(
            [{"role": "user", "content": "hi"}],
            content_ok=lambda text: text.strip().startswith("{"),
        )
    assert answer == '{"answer": 42}'
    assert mock_httpx_client.__enter__.return_value.post.call_count == 2


def test_complete_json_retries_then_succeeds_on_malformed_json(client, monkeypatch):
    malformed = _fake_response(200, "{ { not actually valid json")
    ok = _fake_response(200, '{"questions": [1, 2, 3]}')
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [malformed, ok]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        result = client.complete_json("generate a quiz")
    assert result == {"questions": [1, 2, 3]}
    assert mock_httpx_client.__enter__.return_value.post.call_count == 2


def test_complete_json_rotates_to_next_keys_model_on_malformed_json(
    two_key_client, monkeypatch
):
    # two_key_client has max_retries=1 -> 2 attempts per key before rotating.
    always_malformed = _fake_response(200, "{ { still not valid")
    ok = _fake_response(200, '{"questions": []}')
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.side_effect = [
        always_malformed,
        always_malformed,
        ok,
    ]
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        result = two_key_client.complete_json("generate a quiz")
    assert result == {"questions": []}
    assert mock_httpx_client.__enter__.return_value.post.call_count == 3


def test_complete_json_raises_clear_error_when_every_key_fails(client, monkeypatch):
    always_malformed = _fake_response(200, "definitely not json")
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = always_malformed
    monkeypatch.setattr("time.sleep", lambda *_: None)
    with patch("httpx.Client", return_value=mock_httpx_client):
        with pytest.raises(ValueError, match="content failed validation"):
            client.complete_json("generate a quiz")


def test_complete_json_still_works_with_valid_json_first_try(client, monkeypatch):
    ok = _fake_response(200, '{"questions": [{"question": "hi"}]}')
    mock_httpx_client = MagicMock()
    mock_httpx_client.__enter__.return_value.post.return_value = ok
    with patch("httpx.Client", return_value=mock_httpx_client):
        result = client.complete_json("generate a quiz")
    assert result == {"questions": [{"question": "hi"}]}
    assert mock_httpx_client.__enter__.return_value.post.call_count == 1


# ---------------------------------------------------------------------------
# Streaming (chat_stream), JSON extraction, complete_json and key collection.
# ---------------------------------------------------------------------------
import json as _json  # noqa: E402

from llm_client import (  # noqa: E402
    LLMNotConfigured,
    _collect_api_keys,
    _collect_key_models,
    _extract_json,
)


def _stream_response(status_code=200, lines=None):
    """Context-manager stand-in for httpx's client.stream(...) response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.iter_lines.return_value = iter(lines or [])
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


def _sse(*deltas, done=True):
    lines = [
        "data: " + _json.dumps({"choices": [{"delta": {"content": d}}]}) for d in deltas
    ]
    lines.insert(1, "")  # blank keep-alive line
    lines.insert(1, ": comment line ignored")
    if done:
        lines.append("data: [DONE]")
    return lines


def _stream_client(responses):
    """Patch httpx.Client so each client.stream() call returns the next response."""
    http = MagicMock()
    http.__enter__.return_value.stream.side_effect = responses
    return patch("httpx.Client", return_value=http)


class TestChatStream:
    def test_yields_deltas_in_order(self):
        c = LLMClient(api_key="k")
        with _stream_client([_stream_response(200, _sse("Hel", "lo ", "world"))]):
            assert (
                "".join(c.chat_stream([{"role": "user", "content": "hi"}]))
                == "Hello world"
            )

    def test_stops_without_done_marker(self):
        c = LLMClient(api_key="k")
        with _stream_client([_stream_response(200, _sse("a", "b", done=False))]):
            assert list(c.chat_stream([])) == ["a", "b"]

    def test_empty_and_contentless_chunks_are_skipped(self):
        c = LLMClient(api_key="k")
        lines = ['data: {"choices": [{"delta": {}}]}', 'data: {"choices": []}'] + _sse(
            "x"
        )
        with _stream_client([_stream_response(200, lines)]):
            assert list(c.chat_stream([])) == ["x"]

    def test_rotates_to_next_key_on_rejected_connection(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
        monkeypatch.setenv("OPENROUTER_API_KEY_2", "key-two")
        c = LLMClient()
        with _stream_client([_stream_response(401), _stream_response(200, _sse("ok"))]):
            assert list(c.chat_stream([])) == ["ok"]

    def test_all_keys_rejected_raises_last_error(self):
        c = LLMClient(api_key="k")
        with _stream_client([_stream_response(402)]):
            with pytest.raises(httpx.HTTPStatusError):
                list(c.chat_stream([]))

    def test_network_error_before_start_tries_next_key_then_raises(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
        monkeypatch.setenv("OPENROUTER_API_KEY_2", "key-two")
        c = LLMClient()

        def refuse(*args, **kwargs):
            raise httpx.ConnectError("refused")

        with _stream_client(refuse):
            with pytest.raises(httpx.ConnectError):
                list(c.chat_stream([]))

    def test_failure_after_content_started_is_not_retried(self):
        c = LLMClient(api_key="k")

        def lines():
            yield "data: " + _json.dumps(
                {"choices": [{"delta": {"content": "partial"}}]}
            )
            raise httpx.ReadError("connection dropped")

        resp = _stream_response(200)
        resp.__enter__.return_value.iter_lines.return_value = lines()
        with _stream_client([resp]):
            gen = c.chat_stream([])
            assert next(gen) == "partial"
            with pytest.raises(httpx.ReadError):
                next(gen)

    def test_http_error_after_acceptance_raises(self):
        c = LLMClient(api_key="k")
        with _stream_client([_stream_response(400)]):
            with pytest.raises(httpx.HTTPStatusError):
                list(c.chat_stream([]))

    def test_not_configured(self, monkeypatch):
        for name in (
            "OPENROUTER_API_KEY",
            "OPENROUTER_API_KEY_2",
            "OPENROUTER_API_KEY_3",
        ):
            monkeypatch.delenv(name, raising=False)
        with pytest.raises(LLMNotConfigured):
            list(LLMClient(api_key=None).chat_stream([]))


class TestExtractJson:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ('{"a": 1}', {"a": 1}),
            ('```json\n{"a": 1}\n```', {"a": 1}),
            ("```\n[1, 2]\n```", [1, 2]),
            ('Sure! Here you go: {"a": [1, 2]} hope that helps', {"a": [1, 2]}),
            ("Result: [1, 2, 3] done", [1, 2, 3]),
        ],
    )
    def test_parses_common_llm_wrappers(self, text, expected):
        assert _extract_json(text) == expected

    @pytest.mark.parametrize("text", ["no json here", "{broken", "} reversed {", ""])
    def test_unparseable_raises_value_error(self, text):
        with pytest.raises(ValueError):
            _extract_json(text)


class TestCompleteHelpers:
    def test_complete_builds_system_and_user_messages(self):
        c = LLMClient(api_key="k")
        with patch.object(c, "chat", return_value="answer") as chat:
            assert c.complete("question", system="be brief") == "answer"
        messages = chat.call_args.args[0]
        assert [m["role"] for m in messages] == ["system", "user"]

    def test_complete_without_system(self):
        c = LLMClient(api_key="k")
        with patch.object(c, "chat", return_value="x") as chat:
            c.complete("q")
        assert [m["role"] for m in chat.call_args.args[0]] == ["user"]

    def test_complete_json_parses_fenced_response(self):
        c = LLMClient(api_key="k")

        def fake_chat(messages, content_ok=None, **kw):
            assert kw["json_mode"] is True and kw["temperature"] == 0.2
            assert content_ok('```json\n{"ok": true}\n```')
            assert not content_ok("not json")
            return "ignored"

        with patch.object(c, "chat", side_effect=fake_chat):
            assert c.complete_json("give json", system="sys") == {"ok": True}


class TestConfiguration:
    def test_no_keys_means_not_configured(self, monkeypatch):
        for name in (
            "OPENROUTER_API_KEY",
            "OPENROUTER_API_KEY_2",
            "OPENROUTER_API_KEY_3",
        ):
            monkeypatch.delenv(name, raising=False)
        assert LLMClient().is_configured() is False
        assert _collect_key_models(None, 0, "m") == []

    def test_duplicate_keys_are_collapsed(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "same")
        monkeypatch.setenv("OPENROUTER_API_KEY_2", "same")
        monkeypatch.setenv("OPENROUTER_API_KEY_3", "other")
        assert _collect_api_keys(None) == ["same", "other"]

    def test_per_key_model_overrides(self, monkeypatch):
        for i in range(2, 10):
            monkeypatch.delenv(f"OPENROUTER_MODEL_{i}", raising=False)
        monkeypatch.setenv("OPENROUTER_MODEL_2", "model-b")
        assert _collect_key_models(None, 3, "model-a") == [
            "model-a",
            "model-b",
            "model-a",
        ]
        assert _collect_key_models("forced", 2, "model-a") == ["forced", "forced"]

    def test_get_llm_returns_singleton(self, monkeypatch):
        import llm_client

        monkeypatch.setattr(llm_client, "_default_client", None)
        assert llm_client.get_llm() is llm_client.get_llm()
