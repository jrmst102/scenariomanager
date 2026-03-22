#!/usr/bin/env python3
"""Provision demo data: syncs DecisionLab users, creates sample problems, and loads .SCN fixtures.

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

# ── DecisionLab classlist ────────────────────────────────────────────
CLASSLIST = [
    {"first": "Jose", "last": "Mendoza", "email": "jm10697@nyu.edu", "password": "LimeKoala1!", "role": "admin"},
    {"first": "Jose", "last": "Mendoza", "email": "josermendoza@icloud.com", "password": "LimeKoala1!", "role": "admin"},
    {"first": "Montserrat", "last": "Avila Muñoz", "email": "ma9876@nyu.edu", "password": "RedLion1", "role": "user"},
    {"first": "Carlos", "last": "Bernal", "email": "cab10151@nyu.edu", "password": "BlueTiger2", "role": "user"},
    {"first": "Annika", "last": "Brown", "email": "anb6060@nyu.edu", "password": "GreenBear3", "role": "user"},
    {"first": "Valerie", "last": "Cadena", "email": "vac340@nyu.edu", "password": "YellowWolf4", "role": "user"},
    {"first": "Juan Pablo", "last": "Cajiga Gordillo", "email": "jcg533@nyu.edu", "password": "OrangeDeer5", "role": "user"},
    {"first": "Charlotte", "last": "Detwiler", "email": "cd4020@nyu.edu", "password": "PurpleEagle6", "role": "user"},
    {"first": "Chris", "last": "Dillmeier", "email": "cwd8685@nyu.edu", "password": "WhiteFox7", "role": "user"},
    {"first": "Xuke", "last": "Feng", "email": "xf931@nyu.edu", "password": "BlackHawk8", "role": "user"},
    {"first": "Keri", "last": "Kaleja", "email": "kk5887@nyu.edu", "password": "SilverLynx9", "role": "user"},
    {"first": "Hallie", "last": "Lau", "email": "hl6614@nyu.edu", "password": "GoldPanda1", "role": "user"},
    {"first": "Natalie", "last": "Lee", "email": "nl3125@nyu.edu", "password": "BrownOtter2", "role": "user"},
    {"first": "Jiayi", "last": "Li", "email": "jl17781@nyu.edu", "password": "TealRaven3", "role": "user"},
    {"first": "Xinjue", "last": "Li", "email": "xl6160@nyu.edu", "password": "PinkShark4", "role": "user"},
    {"first": "Cheryl", "last": "Liang", "email": "chl6920@nyu.edu", "password": "GrayWhale5", "role": "user"},
    {"first": "Weilin", "last": "Liang", "email": "wl3557@nyu.edu", "password": "VioletZebra6", "role": "user"},
    {"first": "Camila", "last": "Lievano", "email": "mcl9746@nyu.edu", "password": "IndigoSwan7", "role": "user"},
    {"first": "Skylar", "last": "Lin", "email": "rl5858@nyu.edu", "password": "MaroonOwl8", "role": "user"},
    {"first": "Juliana", "last": "Martinez Aparicio", "email": "jm11756@nyu.edu", "password": "NavyFalcon9", "role": "user"},
    {"first": "Kristen", "last": "Miao", "email": "jm11696@nyu.edu", "password": "AquaDolphin2", "role": "user"},
    {"first": "Vanessa Cibelle", "last": "Moura Caxias", "email": "vm2806@nyu.edu", "password": "CoralCheetah3", "role": "user"},
    {"first": "Jiaying", "last": "Pan", "email": "jp7862@nyu.edu", "password": "BeigeBadger4", "role": "user"},
    {"first": "Sasha", "last": "Rachmadi", "email": "sfr9778@nyu.edu", "password": "CyanCobra5", "role": "user"},
    {"first": "Lanie", "last": "Veazey", "email": "lmv9494@nyu.edu", "password": "MagentaMoose6", "role": "user"},
    {"first": "Senette", "last": "Wiah", "email": "sw7168@nyu.edu", "password": "OliveOcelot7", "role": "user"},
    {"first": "Fangyuan", "last": "Zheng", "email": "fz2481@nyu.edu", "password": "PeachPython8", "role": "user"},
    {"first": "Haihua", "last": "Zhu", "email": "hz4386@nyu.edu", "password": "RubyRhino9", "role": "user"},
]


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

    # --- Sync users from classlist (always overwrite) ---
    users = []
    for entry in CLASSLIST:
        users.append({
            "id": str(uuid.uuid4()),
            "username": entry["email"].split("@")[0],
            "passwordHash": hash_password(entry["password"]),
            "role": entry["role"],
            "displayName": f"{entry['first']} {entry['last']}",
            "email": entry["email"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "loginAttempts": 0,
            "locked": False,
            "lastLogin": None,
        })
    await storage.write_json(USERS_KEY, {"users": users})
    print(f"Synced {len(users)} users from DecisionLab classlist.")

    # --- Sample problem for first admin user ---
    user_id = users[0]["id"]

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
