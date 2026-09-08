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
