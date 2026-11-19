"""
Auth API — signup/login/logout/me for the local/mock Student layer.

Included into backend.py the same way study_api.py is:

    from auth_api import router as auth_router
    app.include_router(auth_router)

get_current_student() is the FastAPI dependency every other protected route
(backend.py's /api/process-lecture, study_api.py's /api/lecture/* routes)
imports to require a logged-in student and get their id.
"""

import logging
import threading
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from auth_utils import (
    validate_email,
    validate_name,
    validate_password,
    validate_username,
)
from student_repository import get_repository, UsernameTakenError
from session_store import get_session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str
    password: str
    confirm_password: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Brute-force protection: too many failed logins for one username inside the
# window locks that username out until the window passes. In-memory (resets on
# restart), which is fine for the local/mock auth layer.
MAX_FAILED_LOGINS = 5
LOCKOUT_WINDOW_S = 300
_failed_logins: Dict[str, List[float]] = {}
_failed_lock = threading.Lock()


def _recent_failures(key: str, now: float) -> List[float]:
    """Failures for `key` still inside the window (prunes the rest). Hold _failed_lock."""
    recent = [t for t in _failed_logins.get(key, []) if now - t < LOCKOUT_WINDOW_S]
    if recent:
        _failed_logins[key] = recent
    else:
        _failed_logins.pop(key, None)
    return recent


def get_current_student(authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency: returns the authenticated student's id, or raises 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    student_id = get_session_store().resolve(token)
    if student_id is None:
        raise HTTPException(
            status_code=401, detail="Session expired or invalid — please log in again"
        )
    return student_id


def get_optional_student(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Like get_current_student but returns None instead of raising - for
    routes that behave differently when logged in vs not, without requiring it."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return get_session_store().resolve(token)


@router.post("/signup")
async def signup(body: SignupRequest):
    username = (body.username or "").strip()
    error = (
        validate_username(username)
        or validate_name(body.name)
        or validate_email(body.email)
        or validate_password(body.password, username)
    )
    if error is None and body.confirm_password is not None:
        if body.confirm_password != body.password:
            error = "Passwords do not match."
    if error:
        raise HTTPException(status_code=400, detail=error)

    repo = get_repository()
    try:
        record = repo.create(
            username, body.password, (body.name or "").strip() or None, body.email
        )
    except UsernameTakenError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = get_session_store().create(record["id"])
    logger.info(f"New student signed up: {record['username']}")
    return {"token": token, "student": repo.public(record)}


@router.post("/login")
async def login(body: LoginRequest):
    key = (body.username or "").strip().lower()
    now = time.time()
    with _failed_lock:
        recent = _recent_failures(key, now)
    if len(recent) >= MAX_FAILED_LOGINS:
        minutes = max(int(LOCKOUT_WINDOW_S - (now - recent[0])) // 60 + 1, 1)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {minutes} minute(s).",
        )

    repo = get_repository()
    record = repo.authenticate(body.username, body.password)
    if record is None:
        with _failed_lock:
            _failed_logins.setdefault(key, []).append(now)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    with _failed_lock:
        _failed_logins.pop(key, None)

    token = get_session_store().create(record["id"])
    logger.info(f"Student logged in: {record['username']}")
    return {"token": token, "student": repo.public(record)}


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.lower().startswith("bearer "):
        get_session_store().revoke(authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@router.get("/me")
async def me(student_id: str = Depends(get_current_student)):
    repo = get_repository()
    record = repo.get(student_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return repo.public(record)
