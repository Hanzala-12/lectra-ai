"""
Password hashing + session token helpers for the local/mock auth layer.

No bcrypt/passlib/argon2 installed in this environment, so this uses stdlib
hashlib.pbkdf2_hmac (PBKDF2-HMAC-SHA256, per-user random salt, 260k
iterations — in line with current OWASP guidance for PBKDF2-SHA256). This is
a real, correct password-hashing scheme, not a placeholder — passwords are
never stored or logged in plaintext anywhere.

This whole layer is intentionally simple/local (JSON-file backed, see
student_repository.py) — the plan is to replace it with a real provider
(e.g. Supabase) later without changing the API surface much.
"""

import hashlib
import hmac
import os
import secrets

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """Return 'salt$hash' (both hex) for storage."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time compare against a 'salt$hash' string from hash_password()."""
    try:
        salt, expected_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), expected_hex)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)
