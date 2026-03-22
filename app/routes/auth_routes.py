"""Authentication routes: login, logout, session, password change."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

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

USERS_KEY = "data/users.json"
MAX_LOGIN_ATTEMPTS = 3


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
