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
