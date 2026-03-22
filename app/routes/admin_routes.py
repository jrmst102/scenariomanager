"""Admin routes: user CRUD, account unlock, password reset."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel

from app.auth.login_manager import require_admin
from app.auth.password_manager import hash_password
from app.storage.store import storage

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

USERS_KEY = "data/users.json"


async def _get_users() -> list[dict]:
    data = await storage.read_json(USERS_KEY)
    if data is None:
        return []
    return data if isinstance(data, list) else data.get("users", [])


async def _save_users(users: list[dict]) -> None:
    await storage.write_json(USERS_KEY, {"users": users})


# --- Page ---

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, user: dict = Depends(require_admin)):
    users = await _get_users()
    # Strip password hashes from response
    safe_users = [{k: v for k, v in u.items() if k != "passwordHash"} for u in users]
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "user": user,
        "users": safe_users,
    })


# --- API ---

@router.get("/api/v1/admin/users")
async def list_users(user: dict = Depends(require_admin)):
    users = await _get_users()
    return [{k: v for k, v in u.items() if k != "passwordHash"} for u in users]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


@router.post("/api/v1/admin/users")
async def create_user(body: CreateUserRequest, user: dict = Depends(require_admin)):
    users = await _get_users()

    # Check duplicate username
    if any(u["username"] == body.username for u in users):
        raise HTTPException(status_code=400, detail="Username already exists")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    new_user = {
        "id": str(uuid.uuid4()),
        "username": body.username,
        "passwordHash": hash_password(body.password),
        "role": body.role,
        "locked": False,
        "loginAttempts": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "lastLogin": None,
    }
    users.append(new_user)
    await _save_users(users)
    return {"userId": new_user["id"], "message": "User created"}


class UpdateUserRequest(BaseModel):
    username: str | None = None
    role: str | None = None


@router.put("/api/v1/admin/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest, user: dict = Depends(require_admin)):
    users = await _get_users()
    target = None
    for u in users:
        if u["id"] == user_id:
            target = u
            break
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if body.username is not None:
        # Check duplicate
        if any(u["username"] == body.username and u["id"] != user_id for u in users):
            raise HTTPException(status_code=400, detail="Username already exists")
        target["username"] = body.username
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
        target["role"] = body.role

    await _save_users(users)
    return {"message": "User updated"}


@router.delete("/api/v1/admin/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_admin)):
    users = await _get_users()
    filtered = [u for u in users if u["id"] != user_id]
    if len(filtered) == len(users):
        raise HTTPException(status_code=404, detail="User not found")
    await _save_users(filtered)
    return {"message": "User deleted"}


@router.post("/api/v1/admin/users/{user_id}/unlock")
async def unlock_user(user_id: str, user: dict = Depends(require_admin)):
    users = await _get_users()
    for u in users:
        if u["id"] == user_id:
            u["locked"] = False
            u["loginAttempts"] = 0
            await _save_users(users)
            return {"message": "User unlocked"}
    raise HTTPException(status_code=404, detail="User not found")


class ResetPasswordRequest(BaseModel):
    newPassword: str


@router.post("/api/v1/admin/users/{user_id}/reset-password")
async def reset_password(user_id: str, body: ResetPasswordRequest, user: dict = Depends(require_admin)):
    if len(body.newPassword) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    users = await _get_users()
    for u in users:
        if u["id"] == user_id:
            u["passwordHash"] = hash_password(body.newPassword)
            u["locked"] = False
            u["loginAttempts"] = 0
            await _save_users(users)
            return {"message": "Password reset"}
    raise HTTPException(status_code=404, detail="User not found")
