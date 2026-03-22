"""Authentication and session management using JWT and signed cookies."""

import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import settings

# Session cookie serializer (itsdangerous)
_session_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET)

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
PARTICIPANT_JWT_EXPIRY_HOURS = 4
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_MINUTES = 15


# ---------- JWT helpers ----------

def create_jwt(payload: dict, expiry_hours: int = JWT_EXPIRY_HOURS) -> str:
    """Create a signed JWT token."""
    payload = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT token. Raises on invalid/expired."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])


def create_participant_jwt(problem_id: str, participant_id: str, token: str) -> str:
    """Create a short-lived JWT for an authenticated participant."""
    return create_jwt(
        {
            "type": "participant",
            "problemId": problem_id,
            "participantId": participant_id,
            "token": token,
        },
        expiry_hours=PARTICIPANT_JWT_EXPIRY_HOURS,
    )


# ---------- Session cookie helpers ----------

def create_session_cookie(user_id: str, role: str) -> str:
    """Sign a session payload."""
    return _session_serializer.dumps({"userId": user_id, "role": role})


def read_session_cookie(cookie_value: str, max_age: int = 86400) -> dict | None:
    """Unsign and return session payload, or None if invalid/expired."""
    try:
        return _session_serializer.loads(cookie_value, max_age=max_age)
    except (BadSignature, Exception):
        return None


# ---------- Cookie-based response helpers ----------

def set_auth_cookie(response: Response, user_id: str, role: str) -> None:
    """Set httpOnly session cookie on response."""
    token = create_jwt({"userId": user_id, "role": role})
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=settings.APP_ENV != "development",
        samesite="lax",
        max_age=JWT_EXPIRY_HOURS * 3600,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Delete session cookie."""
    response.delete_cookie(key="session", path="/")


def set_participant_cookie(
    response: Response, problem_id: str, participant_id: str, token: str
) -> None:
    """Set httpOnly participant session cookie."""
    jwt_token = create_participant_jwt(problem_id, participant_id, token)
    response.set_cookie(
        key=f"participant_{problem_id}",
        value=jwt_token,
        httponly=True,
        secure=settings.APP_ENV != "development",
        samesite="lax",
        max_age=PARTICIPANT_JWT_EXPIRY_HOURS * 3600,
        path="/",
    )


# ---------- Request dependency: get current user ----------

async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and validate user from session cookie.

    Returns dict with userId and role, or raises 401.
    """
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_jwt(token)
        if "userId" not in payload:
            raise HTTPException(status_code=401, detail="Invalid session")
        return {"userId": payload["userId"], "role": payload.get("role", "user")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency: require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_optional_user(request: Request) -> dict | None:
    """Return current user or None (no exception)."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def get_participant_session(request: Request, problem_id: str) -> dict | None:
    """Read participant JWT cookie for a specific problem."""
    token = request.cookies.get(f"participant_{problem_id}")
    if not token:
        return None
    try:
        payload = decode_jwt(token)
        if payload.get("type") != "participant" or payload.get("problemId") != problem_id:
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
