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
import re
import secrets
from typing import Optional

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


# ---------------------------------------------------------------- validation
# Server-side source of truth for signup rules. The frontend mirrors these for
# live feedback (frontend/src/lib/validation.ts) but never replaces them.

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{2,19}$")
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$"
)
# Letters in any script, separated by single spaces / hyphens / apostrophes / dots.
NAME_RE = re.compile(r"^[^\W\d_]+([ .'\-][^\W\d_]+)*\.?$", re.UNICODE)

PASSWORD_MIN = 8
PASSWORD_MAX = 128

# Tiny deny-list of the passwords people actually pick; the complexity rules
# already block most, but "Password1!"-style variants slip through them.
COMMON_PASSWORDS = {
    "password",
    "password1",
    "password1!",
    "password123",
    "passw0rd",
    "p@ssw0rd",
    "p@ssword1",
    "qwerty123",
    "qwerty123!",
    "qwertyuiop",
    "letmein123",
    "welcome1",
    "welcome123",
    "admin123",
    "admin@123",
    "iloveyou1",
    "abc12345",
    "abcd1234",
    "abc123456",
    "12345678",
    "123456789",
    "1234567890",
    "11111111",
    "000000000",
    "changeme",
    "changeme1",
    "lectra123",
    "lectraai1",
    "pakistan1",
    "student123",
}


def validate_username(username: Optional[str]) -> Optional[str]:
    """Return an error message, or None if the username is acceptable."""
    username = (username or "").strip()
    if not username:
        return "Username is required."
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 20:
        return "Username must be at most 20 characters."
    if not (username[0].isascii() and username[0].isalpha()):
        return "Username must start with a letter (not a number)."
    if not USERNAME_RE.match(username):
        return "Username may only contain letters, numbers, underscores and dots."
    if username.endswith(".") or ".." in username:
        return "Username cannot end with a dot or contain two dots in a row."
    return None


def validate_password(
    password: Optional[str], username: Optional[str] = None
) -> Optional[str]:
    """Return the first problem with the password, or None if it is strong enough."""
    if not password:
        return "Password is required."
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters."
    if any(c.isspace() for c in password):
        return "Password cannot contain spaces."
    if not any(c.isupper() for c in password):
        return "Password needs at least one uppercase letter."
    if not any(c.islower() for c in password):
        return "Password needs at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return "Password needs at least one number."
    if all(c.isalnum() for c in password):
        return "Password needs at least one special character (e.g. ! @ # $ %)."
    if re.search(r"(.)\1{2,}", password):
        return "Password cannot repeat the same character three times in a row."
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS:
        return "That password is too common - choose something less guessable."
    uname = (username or "").strip().lower()
    if len(uname) >= 3 and uname in lowered:
        return "Password cannot contain your username."
    return None


def validate_email(email: Optional[str]) -> Optional[str]:
    """Email is optional; if given it must look like a real address."""
    email = (email or "").strip()
    if not email:
        return None
    if len(email) > 254 or not EMAIL_RE.match(email) or ".." in email:
        return "Enter a valid email address (e.g. name@example.com)."
    return None


def validate_name(name: Optional[str]) -> Optional[str]:
    """Full name is optional; if given it must look like a name."""
    name = (name or "").strip()
    if not name:
        return None
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if len(name) > 60:
        return "Name must be at most 60 characters."
    if not NAME_RE.match(name):
        return "Name can only contain letters, spaces, hyphens and apostrophes."
    return None
