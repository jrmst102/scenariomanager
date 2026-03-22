"""Participant CRUD, token generation, and PIN management."""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.auth.password_manager import hash_pin, verify_pin

MAX_PARTICIPANTS = 12
PIN_MAX_ATTEMPTS = 3
PIN_LOCKOUT_MINUTES = 15


def add_participant(problem: dict, name: str, pin: str | None = None) -> dict | None:
    """Add a participant to a problem. Returns the participant dict or None if max reached."""
    if len(problem.get("participants", [])) >= MAX_PARTICIPANTS:
        return None

    participant = {
        "id": str(uuid.uuid4()),
        "name": name,
        "token": str(uuid.uuid4()),
        "pinHash": hash_pin(pin) if pin else None,
        "pinAttempts": 0,
        "pinLockedUntil": None,
        "status": "pending",
        "addedAt": datetime.now(timezone.utc).isoformat(),
    }

    if "participants" not in problem:
        problem["participants"] = []
    problem["participants"].append(participant)
    return participant


def remove_participant(problem: dict, participant_id: str) -> bool:
    """Remove a participant. Returns True if found and removed."""
    before = len(problem.get("participants", []))
    problem["participants"] = [
        p for p in problem.get("participants", []) if p["id"] != participant_id
    ]
    return len(problem["participants"]) < before


def update_participant(problem: dict, participant_id: str, name: str | None = None) -> dict | None:
    """Update participant details. Returns updated participant or None."""
    for p in problem.get("participants", []):
        if p["id"] == participant_id:
            if name is not None:
                p["name"] = name
            return p
    return None


def get_participant_by_token(problem: dict, token: str) -> dict | None:
    """Find a participant by their unique token."""
    for p in problem.get("participants", []):
        if p["token"] == token:
            return p
    return None


def get_participant_by_id(problem: dict, participant_id: str) -> dict | None:
    """Find a participant by ID."""
    for p in problem.get("participants", []):
        if p["id"] == participant_id:
            return p
    return None


def regenerate_token(problem: dict, participant_id: str) -> str | None:
    """Regenerate a participant's token. Returns new token or None."""
    for p in problem.get("participants", []):
        if p["id"] == participant_id:
            p["token"] = str(uuid.uuid4())
            return p["token"]
    return None


def set_pin(problem: dict, participant_id: str, pin: str) -> bool:
    """Set or update a participant's PIN."""
    for p in problem.get("participants", []):
        if p["id"] == participant_id:
            p["pinHash"] = hash_pin(pin)
            p["pinAttempts"] = 0
            p["pinLockedUntil"] = None
            return True
    return False


def verify_participant_pin(participant: dict, pin: str) -> tuple[bool, bool]:
    """Verify a participant's PIN.

    Returns (success, locked_out).
    """
    if not participant.get("pinHash"):
        return True, False  # No PIN required

    # Check lockout
    locked_until = participant.get("pinLockedUntil")
    if locked_until:
        locked_dt = datetime.fromisoformat(locked_until)
        if datetime.now(timezone.utc) < locked_dt:
            return False, True  # Still locked out

    # Verify
    if verify_pin(pin, participant["pinHash"]):
        participant["pinAttempts"] = 0
        participant["pinLockedUntil"] = None
        return True, False

    # Failed attempt
    participant["pinAttempts"] = participant.get("pinAttempts", 0) + 1
    if participant["pinAttempts"] >= PIN_MAX_ATTEMPTS:
        lockout_time = datetime.now(timezone.utc)
        from datetime import timedelta
        participant["pinLockedUntil"] = (lockout_time + timedelta(minutes=PIN_LOCKOUT_MINUTES)).isoformat()

    return False, participant["pinAttempts"] >= PIN_MAX_ATTEMPTS


def update_participant_status(problem: dict, participant_id: str, status: str) -> None:
    """Update a participant's status (pending, in_progress, submitted)."""
    for p in problem.get("participants", []):
        if p["id"] == participant_id:
            p["status"] = status
            break
