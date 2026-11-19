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
        "/api/auth/signup", json={"username": "alice", "password": "Wonder#Land1"}
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
    client.post("/api/auth/signup", json={"username": "bob", "password": "Bu1lder#Pw9"})
    r = client.post(
        "/api/auth/signup", json={"username": "bob", "password": "Diff3rent#Pw"}
    )
    assert r.status_code == 409


def test_signup_duplicate_username_case_insensitive():
    client.post(
        "/api/auth/signup", json={"username": "Carol", "password": "S1nger#Pw99"}
    )
    r = client.post(
        "/api/auth/signup", json={"username": "carol", "password": "Diff3rent#Pw"}
    )
    assert r.status_code == 409


def test_signup_missing_fields_rejected():
    r = client.post("/api/auth/signup", json={"username": "", "password": "x"})
    assert r.status_code == 400


def test_signup_uses_full_name_when_given():
    r = client.post(
        "/api/auth/signup",
        json={"username": "dave", "password": "Gr0hl#Pw123", "name": "Dave Grohl"},
    )
    assert r.json()["student"]["name"] == "Dave Grohl"


def test_signup_defaults_name_to_username():
    r = client.post(
        "/api/auth/signup", json={"username": "erin", "password": "Burn3tt#Pw1"}
    )
    assert r.json()["student"]["name"] == "erin"


# ----------------------------------------------------------------- login


def test_login_correct_credentials():
    client.post(
        "/api/auth/signup", json={"username": "frank", "password": "S1natra#Pw99"}
    )
    r = client.post(
        "/api/auth/login", json={"username": "frank", "password": "S1natra#Pw99"}
    )
    assert r.status_code == 200
    assert r.json()["student"]["username"] == "frank"


def test_login_wrong_password_rejected():
    client.post(
        "/api/auth/signup", json={"username": "grace", "password": "H0pper#Pw123"}
    )
    r = client.post(
        "/api/auth/login", json={"username": "grace", "password": "Wr0ng#Passw0rd"}
    )
    assert r.status_code == 401


def test_login_unknown_username_rejected():
    r = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "Wh@tever123"}
    )
    assert r.status_code == 401


def test_login_is_username_case_insensitive():
    client.post(
        "/api/auth/signup", json={"username": "Henry", "password": "F0rd#Pw1908"}
    )
    r = client.post(
        "/api/auth/login", json={"username": "henry", "password": "F0rd#Pw1908"}
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
        "/api/auth/signup", json={"username": "ivy", "password": "Le@gue#Pw123"}
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
            "password": "Sp@rrow#Pw1",
            "email": "jack@example.com",
        },
    )
    assert r.json()["student"]["email"] == "jack@example.com"


def test_signup_email_is_optional():
    r = client.post(
        "/api/auth/signup", json={"username": "kim", "password": "P0ssible#Pw1"}
    )
    assert r.status_code == 200
    assert r.json()["student"]["email"] is None


# ----------------------------------------------------------------- signup validation

STRONG = "Zebra#Lecture7"


def _signup(**kw):
    body = {"username": "validuser", "password": STRONG}
    body.update(kw)
    return client.post("/api/auth/signup", json=body)


def test_signup_rejects_numeric_only_username():
    r = _signup(username="23454")
    assert r.status_code == 400
    assert "letter" in r.json()["detail"].lower()


def test_signup_rejects_bad_usernames():
    for bad in ["ab", "9lives", "has space", "bad!char", "x" * 21, "dot.", "a..b"]:
        assert _signup(username=bad).status_code == 400, bad


def test_signup_accepts_reasonable_usernames():
    for i, ok in enumerate(["Hanzala", "hanz_ala", "h.anzala2"]):
        assert (
            _signup(username=ok, password=f"Zebra#Lect{i}ure!").status_code == 200
        ), ok


def test_signup_rejects_weak_passwords():
    cases = {
        "Short1!": "at least 8",
        "alllowercase1!": "uppercase",
        "ALLUPPERCASE1!": "lowercase",
        "NoDigitsHere!": "number",
        "NoSpecial1234": "special",
        "Has Space1!x": "spaces",
        "Aaaa#1234567": "repeat",
        "Password1!": "common",
    }
    for pw, expect in cases.items():
        r = _signup(username="weakpw", password=pw)
        assert r.status_code == 400, pw
        assert expect in r.json()["detail"].lower(), (pw, r.json()["detail"])


def test_signup_rejects_password_containing_username():
    r = _signup(username="hanzala", password="Hanzala#2026")
    assert r.status_code == 400
    assert "username" in r.json()["detail"].lower()


def test_signup_confirm_password_must_match_when_sent():
    r = _signup(username="confirmme", confirm_password="Zebra#Lecture8")
    assert r.status_code == 400
    assert "match" in r.json()["detail"].lower()
    assert _signup(username="confirmme", confirm_password=STRONG).status_code == 200


def test_signup_rejects_invalid_email_and_name():
    assert _signup(username="mailtest", email="not-an-email").status_code == 400
    assert _signup(username="nametest", name="J0hn 123").status_code == 400
    assert (
        _signup(
            username="goodmail", email="a.b@nuces.edu.pk", name="Mary-Jane O'Neil"
        ).status_code
        == 200
    )


# ----------------------------------------------------------------- brute-force lockout


def test_login_locks_out_after_repeated_failures():
    import auth_api

    auth_api._failed_logins.clear()
    _signup(username="lockme")
    for _ in range(auth_api.MAX_FAILED_LOGINS):
        r = client.post(
            "/api/auth/login", json={"username": "lockme", "password": "Wr0ng#Guess1"}
        )
        assert r.status_code == 401
    # now even the correct password is refused until the window passes
    r = client.post("/api/auth/login", json={"username": "lockme", "password": STRONG})
    assert r.status_code == 429
    auth_api._failed_logins.clear()
    assert (
        client.post(
            "/api/auth/login", json={"username": "lockme", "password": STRONG}
        ).status_code
        == 200
    )


def test_successful_login_resets_failure_count():
    import auth_api

    auth_api._failed_logins.clear()
    _signup(username="resetme")
    for _ in range(auth_api.MAX_FAILED_LOGINS - 1):
        client.post(
            "/api/auth/login", json={"username": "resetme", "password": "Wr0ng#Guess1"}
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "resetme", "password": STRONG}
        ).status_code
        == 200
    )
    assert "resetme" not in auth_api._failed_logins
