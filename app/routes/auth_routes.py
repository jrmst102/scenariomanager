"""Authentication routes: login, logout, session, password change, SSO."""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.auth.login_manager import (
    clear_auth_cookie,
    get_current_user,
    set_auth_cookie,
)
from app.auth.password_manager import hash_password, verify_password
from app.storage.store import storage

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

logger = logging.getLogger(__name__)

USERS_KEY = "data/users.json"
MAX_LOGIN_ATTEMPTS = 3
TOOL_SSO_SECRET = os.environ.get("TOOL_SSO_SECRET_SCENARIO_SIM") or os.environ.get("TOOL_SSO_SECRET", "tool-sso-secret-change-me")


async def _get_users() -> list[dict]:
    data = await storage.read_json(USERS_KEY)
    if data is None:
        return []
    return data if isinstance(data, list) else data.get("users", [])


async def _save_users(users: list[dict]) -> None:
    await storage.write_json(USERS_KEY, {"users": users})


async def _find_user(username: str) -> dict | None:
    users = await _get_users()
    for u in users:
        if u["username"] == username:
            return u
    return None


async def _update_user(user: dict) -> None:
    users = await _get_users()
    for i, u in enumerate(users):
        if u["id"] == user["id"]:
            users[i] = user
            break
    await _save_users(users)


# --- Page Routes ---

@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


# --- API Routes ---

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/v1/auth/login")
async def login(body: LoginRequest, response: Response):
    user = await _find_user(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check lockout
    if user.get("locked", False):
        raise HTTPException(status_code=423, detail="Account is locked. Contact administrator.")

    if user.get("loginAttempts", 0) >= MAX_LOGIN_ATTEMPTS:
        user["locked"] = True
        await _update_user(user)
        raise HTTPException(status_code=423, detail="Account locked due to too many failed attempts")

    if not verify_password(body.password, user["passwordHash"]):
        user["loginAttempts"] = user.get("loginAttempts", 0) + 1
        await _update_user(user)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Success — reset attempts
    user["loginAttempts"] = 0
    user["lastLogin"] = datetime.now(timezone.utc).isoformat()
    await _update_user(user)

    set_auth_cookie(response, user["id"], user.get("role", "user"))
    return {"message": "Login successful", "userId": user["id"], "role": user.get("role", "user")}


@router.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


@router.post("/auth/change-password")
async def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    full_user = None
    users = await _get_users()
    for u in users:
        if u["id"] == user["userId"]:
            full_user = u
            break

    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.currentPassword, full_user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if len(body.newPassword) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    full_user["passwordHash"] = hash_password(body.newPassword)
    await _update_user(full_user)
    return {"message": "Password changed successfully"}


# ── SSO from DecisionLab ──────────────────────────────────────────────

async def _find_or_create_sso_user(email: str, role: str) -> dict:
    """Find user by email, or create a new one. Returns the user dict."""
    users = await _get_users()
    for u in users:
        if u.get("email", "").strip().lower() == email.strip().lower():
            return u

    # Create new user
    local_part = email.split("@")[0] if "@" in email else email
    new_user = {
        "id": str(uuid.uuid4()),
        "username": local_part,
        "passwordHash": hash_password(uuid.uuid4().hex),
        "role": "admin" if role == "ADMIN" else "user",
        "displayName": local_part.replace(".", " ").title(),
        "email": email,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "loginAttempts": 0,
        "locked": False,
        "lastLogin": None,
    }
    users.append(new_user)
    await _save_users(users)
    return new_user


@router.get("/auth/sso")
async def sso_login(request: Request, token: str = ""):
    """Verify a DecisionLab SSO JWT and establish a session."""
    if not token:
        return RedirectResponse(url="/", status_code=302)

    try:
        payload = pyjwt.decode(token, TOOL_SSO_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        logger.warning("SSO token expired")
        return RedirectResponse(url="/", status_code=302)
    except pyjwt.InvalidTokenError:
        logger.warning("Invalid SSO token")
        return RedirectResponse(url="/", status_code=302)

    email = payload.get("email", "")
    role = payload.get("role", "user")

    if not email:
        return RedirectResponse(url="/", status_code=302)

    try:
        user = await _find_or_create_sso_user(email, role)
    except Exception:
        logger.exception("SSO user provisioning failed")
        return RedirectResponse(url="/", status_code=302)

    redirect_url = "/problems"
    response = RedirectResponse(url=redirect_url, status_code=302)
    set_auth_cookie(response, user["id"], user.get("role", "user"))
    return response
