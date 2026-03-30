"""Problem CRUD operations and .SCN file I/O."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.storage.store import storage

logger = logging.getLogger(__name__)

# In-memory write-through cache: {"userId:problemId": dict}
# Ensures a just-created/saved problem is always readable in the same process,
# even when the storage backend has eventual-consistency delays.
_problem_cache: dict[str, dict] = {}

def _cache_key(user_id: str, problem_id: str) -> str:
    return f"{user_id}:{problem_id}"

# Storage key helpers
def _user_problems_index_key(user_id: str) -> str:
    return f"users/{user_id}/problems/index.json"

def _problem_key(user_id: str, problem_id: str) -> str:
    return f"users/{user_id}/problems/{problem_id}.SCN"


def _problem_lookup_keys(user_id: str, problem_id: str) -> list[str]:
    """Return storage keys to try when loading/deleting a problem.

    `.SCN` is canonical, but we also support legacy extensions that may
    exist in production buckets from older versions.
    """
    base = f"users/{user_id}/problems/{problem_id}"
    return [
        f"{base}.SCN",
        f"{base}.scn",
        f"{base}.json",
        f"{base}.JSON",
    ]


def new_problem_template(title: str = "", description: str = "") -> dict:
    """Return a blank problem with default structure."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "1.0",
        "problemId": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "createdAt": now,
        "updatedAt": now,
        "axes": {
            "x": {
                "label": "",
                "lowPole": {"label": "", "description": ""},
                "highPole": {"label": "", "description": ""},
            },
            "y": {
                "label": "",
                "lowPole": {"label": "", "description": ""},
                "highPole": {"label": "", "description": ""},
            },
        },
        "scenarios": [
            {"id": "Q1", "name": "", "xPole": "high", "yPole": "low", "narrative": ""},
            {"id": "Q2", "name": "", "xPole": "high", "yPole": "high", "narrative": ""},
            {"id": "Q3", "name": "", "xPole": "low", "yPole": "high", "narrative": ""},
            {"id": "Q4", "name": "", "xPole": "low", "yPole": "low", "narrative": ""},
        ],
        "alternatives": [],
        "config": {
            "anonymousMode": False,
            "pinProtected": False,
        },
        "participants": [],
        "rounds": [
            {
                "roundNumber": 1,
                "status": "open",
                "openedAt": now,
                "closedAt": None,
            }
        ],
        "currentRound": 1,
        "assessments": {},
        "report": {
            "narrative": "",
            "generatedAt": None,
            "model": None,
        },
    }


async def get_problems_index(user_id: str) -> list[dict]:
    """Get the list of problems for a user."""
    data = await storage.read_json(_user_problems_index_key(user_id))
    if data is None:
        return []
    return data.get("problems", [])


async def save_problems_index(user_id: str, problems: list[dict]) -> None:
    """Save the problems index for a user."""
    await storage.write_json(_user_problems_index_key(user_id), {"problems": problems})


async def create_problem(user_id: str, title: str = "", description: str = "") -> dict:
    """Create a new problem, save it, and add to index."""
    problem = new_problem_template(title, description)
    problem_id = problem["problemId"]

    # Save the problem file
    await storage.write_json(_problem_key(user_id, problem_id), problem)

    # Cache so the immediate redirect always finds it
    _problem_cache[_cache_key(user_id, problem_id)] = problem
    logger.info("Created problem %s for user %s", problem_id, user_id)

    # Update the index
    index = await get_problems_index(user_id)
    index.append({
        "problemId": problem_id,
        "title": title,
        "updatedAt": problem["updatedAt"],
        "status": "draft",
    })
    await save_problems_index(user_id, index)

    return problem


async def get_problem(user_id: str, problem_id: str) -> dict | None:
    """Load a problem by ID."""
    # Check in-memory cache first (handles write-then-read consistency)
    ck = _cache_key(user_id, problem_id)
    cached = _problem_cache.get(ck)
    if cached is not None:
        return cached

    # Try canonical key first (vast majority of problems)
    primary_key = _problem_key(user_id, problem_id)
    problem = await storage.read_json(primary_key)
    if problem is not None:
        _problem_cache[ck] = problem
        return problem

    # Fall back to legacy extensions only if canonical key missed
    for key in _problem_lookup_keys(user_id, problem_id)[1:]:
        problem = await storage.read_json(key)
        if problem is not None:
            _problem_cache[ck] = problem
            return problem
    logger.warning("Problem not in cache or storage: user=%s problem=%s", user_id, problem_id)
    return None


async def save_problem(user_id: str, problem: dict) -> None:
    """Save a problem (full replacement)."""
    problem["updatedAt"] = datetime.now(timezone.utc).isoformat()
    problem_id = problem["problemId"]
    await storage.write_json(_problem_key(user_id, problem_id), problem)
    _problem_cache[_cache_key(user_id, problem_id)] = problem

    # Update index entry (add if missing — handles eventual-consistency cases
    # where a stale index was read without the newly imported entry)
    index = await get_problems_index(user_id)
    found = False
    for entry in index:
        if entry["problemId"] == problem_id:
            entry["title"] = problem.get("title", "")
            entry["updatedAt"] = problem["updatedAt"]
            found = True
            break
    if not found:
        index.append({
            "problemId": problem_id,
            "title": problem.get("title", ""),
            "updatedAt": problem["updatedAt"],
            "status": "draft",
        })
    await save_problems_index(user_id, index)


async def delete_problem(user_id: str, problem_id: str) -> bool:
    """Delete a problem and remove from index."""
    _problem_cache.pop(_cache_key(user_id, problem_id), None)
    deleted = False
    for key in _problem_lookup_keys(user_id, problem_id):
        deleted = await storage.delete(key) or deleted

    index = await get_problems_index(user_id)
    index = [p for p in index if p["problemId"] != problem_id]
    await save_problems_index(user_id, index)

    return deleted


def validate_scn_file(data: Any) -> dict | None:
    """Validate an imported .SCN file. Returns the parsed dict or None."""
    if not isinstance(data, dict):
        return None
    required = ["version", "problemId", "title", "axes", "scenarios", "alternatives"]
    if not all(k in data for k in required):
        return None
    if data.get("version") != "1.0":
        return None
    return data


async def import_problem(user_id: str, data: dict) -> dict | None:
    """Import a .SCN file — assign new IDs and save."""
    validated = validate_scn_file(data)
    if validated is None:
        return None

    # Assign new problem ID to avoid collisions
    now = datetime.now(timezone.utc).isoformat()
    validated["problemId"] = str(uuid.uuid4())
    validated["createdAt"] = now
    validated["updatedAt"] = now

    await storage.write_json(_problem_key(user_id, validated["problemId"]), validated)
    _problem_cache[_cache_key(user_id, validated["problemId"])] = validated

    index = await get_problems_index(user_id)
    index.append({
        "problemId": validated["problemId"],
        "title": validated.get("title", "Imported Problem"),
        "updatedAt": now,
        "status": "imported",
    })
    await save_problems_index(user_id, index)

    return validated
