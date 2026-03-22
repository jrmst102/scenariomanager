#!/usr/bin/env python3
"""Provision demo data: creates an admin user, a sample problem, and loads .SCN fixtures.

Usage:
    python -m scripts.provision_demo
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure local_data exists before imports that may reference it
LOCAL_DATA = Path(__file__).resolve().parent.parent / "local_data"
LOCAL_DATA.mkdir(parents=True, exist_ok=True)

from app.auth.password_manager import hash_password
from app.core.problems import new_problem_template
from app.storage.store import storage

USERS_KEY = "data/users.json"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

ADMIN_USER = {
    "id": str(uuid.uuid4()),
    "username": "admin",
    "passwordHash": "",  # filled below
    "role": "admin",
    "displayName": "Administrator",
    "createdAt": datetime.now(timezone.utc).isoformat(),
    "loginAttempts": 0,
    "locked": False,
    "lastLogin": None,
}

DEMO_USER = {
    "id": str(uuid.uuid4()),
    "username": "analyst",
    "passwordHash": "",
    "role": "user",
    "displayName": "Demo Analyst",
    "createdAt": datetime.now(timezone.utc).isoformat(),
    "loginAttempts": 0,
    "locked": False,
    "lastLogin": None,
}


def _build_sample_problem() -> dict:
    """Build the Vela Skincare sample problem from the spec."""
    p = new_problem_template(
        title="Vela Skincare — EU Market Entry",
        description="Should Vela enter the EU prestige skincare market by 2026, given regulatory and competitive uncertainty?",
    )
    p["axes"] = {
        "x": {
            "label": "Regulatory Environment",
            "lowPole": {"label": "Fragmented", "description": "National regulations dominate; no unified EU standard emerges by 2027."},
            "highPole": {"label": "Harmonised", "description": "A single EU-wide clean-beauty standard is enacted by 2026."},
        },
        "y": {
            "label": "Competitive Landscape",
            "lowPole": {"label": "Oligopoly", "description": "Three dominant incumbents control ≥ 60 % market share."},
            "highPole": {"label": "Fragmented", "description": "No single player holds > 15 %; many DTC challengers."},
        },
    }
    p["scenarios"] = [
        {"id": "Q1", "name": "Regulated Playground", "xPole": "high", "yPole": "low", "narrative": "Unified rules but a few strong incumbents."},
        {"id": "Q2", "name": "Open Green Field", "xPole": "high", "yPole": "high", "narrative": "Clear standards, many small challengers."},
        {"id": "Q3", "name": "Wild West", "xPole": "low", "yPole": "high", "narrative": "No unified regulations, lots of small players."},
        {"id": "Q4", "name": "Fortress Europe", "xPole": "low", "yPole": "low", "narrative": "Fragmented rules, dominated by incumbents."},
    ]
    p["alternatives"] = [
        {"id": "A", "label": "Full acquisition of a local brand", "description": "Acquire a mid-sized EU-based brand with existing distribution."},
        {"id": "B", "label": "Organic DTC launch", "description": "Build own e-commerce presence from scratch."},
        {"id": "C", "label": "Joint venture with EU retailer", "description": "Partner with a major beauty retailer for exclusive distribution."},
        {"id": "D", "label": "License technology to local manufacturer", "description": "License proprietary formulations to an EU manufacturer."},
        {"id": "E", "label": "Wait and monitor", "description": "Defer entry; continue monitoring regulatory developments."},
    ]
    return p


async def provision():
    await storage.initialize()

    # --- Users ---
    existing = await storage.read_json(USERS_KEY)
    if existing and len(existing.get("users", [])) > 0:
        print("Users already exist — skipping user creation.")
        print("  Existing users:", [u["username"] for u in existing["users"]])
    else:
        ADMIN_USER["passwordHash"] = hash_password("admin123")
        DEMO_USER["passwordHash"] = hash_password("analyst123")
        await storage.write_json(USERS_KEY, {"users": [ADMIN_USER, DEMO_USER]})
        print("Created users:")
        print(f"  admin / admin123  (role: admin)")
        print(f"  analyst / analyst123  (role: user)")

    # --- Sample problem for demo user ---
    user_id = DEMO_USER["id"]
    # Re-read users to get actual IDs if they already existed
    users_data = await storage.read_json(USERS_KEY)
    for u in users_data.get("users", []):
        if u["username"] == "analyst":
            user_id = u["id"]
            break

    index_key = f"users/{user_id}/problems/index.json"
    index = await storage.read_json(index_key)
    existing_problems = index.get("problems", []) if index else []

    # --- Vela Skincare sample (built-in) ---
    vela_exists = any(p["title"].startswith("Vela Skincare") for p in existing_problems)
    if not vela_exists:
        problem = _build_sample_problem()
        problem_id = problem["problemId"]
        await storage.write_json(f"users/{user_id}/problems/{problem_id}.SCN", problem)
        existing_problems.append({
            "problemId": problem_id,
            "title": problem["title"],
            "updatedAt": problem["updatedAt"],
            "status": "draft",
        })
        print(f"Created sample problem: '{problem['title']}' (id: {problem_id})")
    else:
        print("Vela Skincare problem already exists — skipping.")

    # --- Load .SCN fixtures from docs/ ---
    for scn_file in sorted(DOCS_DIR.glob("*.SCN")):
        scn_data = json.loads(scn_file.read_text(encoding="utf-8"))
        scn_id = scn_data["problemId"]
        scn_title = scn_data["title"]

        if any(p["problemId"] == scn_id for p in existing_problems):
            print(f"SCN fixture already loaded: '{scn_title}' — skipping.")
            continue

        await storage.write_json(f"users/{user_id}/problems/{scn_id}.SCN", scn_data)
        existing_problems.append({
            "problemId": scn_id,
            "title": scn_title,
            "updatedAt": scn_data.get("updatedAt", datetime.now(timezone.utc).isoformat()),
            "status": "closed" if scn_data.get("rounds", [{}])[-1].get("status") == "closed" else "draft",
        })
        print(f"Loaded SCN fixture: '{scn_title}' (id: {scn_id})")

    await storage.write_json(index_key, {"problems": existing_problems})

    print("\nDone. Start the app with: python run.py")


if __name__ == "__main__":
    asyncio.run(provision())
