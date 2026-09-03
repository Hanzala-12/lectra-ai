"""
Auth API tests — signup, login, logout, me, and password hashing itself.

Isolation comes from conftest.py's autouse isolated_repos fixture, so none of
this touches real data/students/ or data/sessions.json.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))  # tests/ itself, for `import conftest`

from conftest import client
from auth_utils import hash_password, verify_password


# ----------------------------------------------------------------- signup


def test_signup_creates_a_working_session():
    r = client.post(
        "/api/auth/signup", json={"username": "alice", "password": "wonderland1"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["student"]["username"] == "alice"
    assert "password" not in body["student"]
    assert "password_hash" not in body["student"]
    assert body["token"]

    # the returned token actually works
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_signup_duplicate_username_rejected():
    client.post("/api/auth/signup", json={"username": "bob", "password": "builder1"})
    r = client.post(
        "/api/auth/signup", json={"username": "bob", "password": "different1"}
    )
    assert r.status_code == 409


def test_signup_duplicate_username_case_insensitive():
    client.post("/api/auth/signup", json={"username": "Carol", "password": "singer1"})
    r = client.post(
        "/api/auth/signup", json={"username": "carol", "password": "different1"}
    )
    assert r.status_code == 409


def test_signup_missing_fields_rejected():
    r = client.post("/api/auth/signup", json={"username": "", "password": "x"})
    assert r.status_code == 400


def test_signup_uses_full_name_when_given():
    r = client.post(
        "/api/auth/signup",
        json={"username": "dave", "password": "grohl123", "name": "Dave Grohl"},
    )
    assert r.json()["student"]["name"] == "Dave Grohl"


def test_signup_defaults_name_to_username():
    r = client.post(
        "/api/auth/signup", json={"username": "erin", "password": "burnett1"}
    )
    assert r.json()["student"]["name"] == "erin"


# ----------------------------------------------------------------- login


def test_login_correct_credentials():
    client.post("/api/auth/signup", json={"username": "frank", "password": "sinatra99"})
    r = client.post(
        "/api/auth/login", json={"username": "frank", "password": "sinatra99"}
    )
    assert r.status_code == 200
    assert r.json()["student"]["username"] == "frank"


def test_login_wrong_password_rejected():
    client.post("/api/auth/signup", json={"username": "grace", "password": "hopper123"})
    r = client.post(
        "/api/auth/login", json={"username": "grace", "password": "wrongpass"}
    )
    assert r.status_code == 401


def test_login_unknown_username_rejected():
    r = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert r.status_code == 401


def test_login_is_username_case_insensitive():
    client.post("/api/auth/signup", json={"username": "Henry", "password": "ford1908"})
    r = client.post(
        "/api/auth/login", json={"username": "henry", "password": "ford1908"}
    )
    assert r.status_code == 200


# ----------------------------------------------------------------- session lifecycle


def test_me_without_token_401():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_garbage_token_401():
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_logout_invalidates_the_token():
    r = client.post(
        "/api/auth/signup", json={"username": "ivy", "password": "league123"}
    )
    headers = {"Authorization": f"Bearer {r.json()['token']}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200
    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


# ----------------------------------------------------------------- password hashing


def test_password_hash_never_equals_plaintext():
    hashed = hash_password("12345678")
    assert hashed != "12345678"
    assert "12345678" not in hashed


def test_password_verify_roundtrip():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_password_hash_is_salted_differently_each_time():
    """Same password, hashed twice, must produce different stored strings
    (per-user random salt) — otherwise identical passwords would be
    detectable by comparing hashes."""
    assert hash_password("same-password") != hash_password("same-password")


# ----------------------------------------------------------------- email field


def test_signup_stores_and_returns_email():
    r = client.post(
        "/api/auth/signup",
        json={
            "username": "jack",
            "password": "sparrow123",
            "email": "jack@example.com",
        },
    )
    assert r.json()["student"]["email"] == "jack@example.com"


def test_signup_email_is_optional():
    r = client.post(
        "/api/auth/signup", json={"username": "kim", "password": "possible1"}
    )
    assert r.status_code == 200
    assert r.json()["student"]["email"] is None
