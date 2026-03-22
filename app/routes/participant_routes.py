"""Participant routes: tokenized links, PIN verification, assessments."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth.login_manager import (
    get_current_user,
    get_participant_session,
    set_participant_cookie,
)
from app.config import settings
from app.core.assessments import (
    count_completed_cells,
    get_assessment,
    save_assessment,
)
from app.core.participants import (
    add_participant,
    get_participant_by_id,
    get_participant_by_token,
    regenerate_token,
    remove_participant,
    set_pin,
    update_participant,
    update_participant_status,
    verify_participant_pin,
)
from app.core.problems import get_problem, save_problem
from app.core.rounds import is_round_open
from app.storage.store import storage

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

limiter = Limiter(key_func=get_remote_address)


# --- Owner API: Manage Participants ---

class AddParticipantRequest(BaseModel):
    name: str
    pin: str | None = None


@router.get("/api/v1/problems/{problem_id}/participants")
async def list_participants(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    participants = []
    for p in problem.get("participants", []):
        participants.append({
            "id": p["id"],
            "name": p["name"],
            "token": p["token"],
            "status": p["status"],
            "addedAt": p["addedAt"],
            "hasPIN": bool(p.get("pinHash")),
            "link": f"{settings.APP_URL}/participate/{problem_id}/{p['token']}",
        })
    return participants


@router.post("/api/v1/problems/{problem_id}/participants")
async def add_participant_api(problem_id: str, body: AddParticipantRequest, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    participant = add_participant(problem, body.name, body.pin)
    if participant is None:
        raise HTTPException(status_code=400, detail="Maximum 12 participants reached")

    await save_problem(user["userId"], problem)
    return {
        "participant": {
            "id": participant["id"],
            "name": participant["name"],
            "token": participant["token"],
            "link": f"{settings.APP_URL}/participate/{problem_id}/{participant['token']}",
        },
        "message": "Participant added",
    }


@router.put("/api/v1/problems/{problem_id}/participants/{participant_id}")
async def update_participant_api(
    problem_id: str, participant_id: str, body: AddParticipantRequest, user: dict = Depends(get_current_user)
):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    result = update_participant(problem, participant_id, body.name)
    if result is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    if body.pin:
        set_pin(problem, participant_id, body.pin)
    await save_problem(user["userId"], problem)
    return {"message": "Participant updated"}


@router.delete("/api/v1/problems/{problem_id}/participants/{participant_id}")
async def remove_participant_api(problem_id: str, participant_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if not remove_participant(problem, participant_id):
        raise HTTPException(status_code=404, detail="Participant not found")
    await save_problem(user["userId"], problem)
    return {"message": "Participant removed"}


@router.post("/api/v1/problems/{problem_id}/participants/{participant_id}/regenerate-pin")
async def regenerate_pin_api(problem_id: str, participant_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    new_token = regenerate_token(problem, participant_id)
    if new_token is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    await save_problem(user["userId"], problem)
    return {
        "token": new_token,
        "link": f"{settings.APP_URL}/participate/{problem_id}/{new_token}",
        "message": "Token regenerated",
    }


# --- Config ---

class ConfigRequest(BaseModel):
    anonymousMode: bool | None = None
    pinProtected: bool | None = None


@router.put("/api/v1/problems/{problem_id}/config")
async def update_config(problem_id: str, body: ConfigRequest, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if body.anonymousMode is not None:
        problem["config"]["anonymousMode"] = body.anonymousMode
    if body.pinProtected is not None:
        problem["config"]["pinProtected"] = body.pinProtected
    await save_problem(user["userId"], problem)
    return {"message": "Config updated"}


# --- Rounds ---

from app.core.rounds import close_round, new_round, reopen_round, finalize_problem


@router.post("/api/v1/problems/{problem_id}/round/close")
async def close_round_api(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if not close_round(problem):
        raise HTTPException(status_code=400, detail="Round cannot be closed")
    await save_problem(user["userId"], problem)
    return {"message": "Round closed"}


@router.post("/api/v1/problems/{problem_id}/round/reopen")
async def reopen_round_api(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if not reopen_round(problem):
        raise HTTPException(status_code=400, detail="Round cannot be reopened")
    await save_problem(user["userId"], problem)
    return {"message": "Round reopened"}


@router.post("/api/v1/problems/{problem_id}/round/new")
async def new_round_api(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    round_obj = new_round(problem)
    await save_problem(user["userId"], problem)
    return {"message": "New round opened", "round": round_obj}


@router.post("/api/v1/problems/{problem_id}/finalize")
async def finalize_api(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    finalize_problem(problem)
    await save_problem(user["userId"], problem)
    return {"message": "Problem finalized"}


# --- Consensus & Rounds History ---

@router.get("/api/v1/problems/{problem_id}/rounds")
async def get_rounds(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return {
        "currentRound": problem.get("currentRound", 1),
        "rounds": problem.get("rounds", []),
    }


# --- Participant-facing Routes ---

@router.get("/participate/{problem_id}/{token}", response_class=HTMLResponse)
async def participate_entry(request: Request, problem_id: str, token: str):
    """Entry point for participants: show PIN page or redirect to assessment."""
    # Find the problem across all users
    problem, user_id = await _find_problem_by_participant_token(problem_id, token)
    if not problem:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    participant = get_participant_by_token(problem, token)
    if not participant:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    # If PIN required and no valid session, show PIN page
    if participant.get("pinHash"):
        session = await get_participant_session(request, problem_id)
        if not session or session.get("participantId") != participant["id"]:
            return templates.TemplateResponse("participate_pin.html", {
                "request": request,
                "problem_id": problem_id,
                "token": token,
                "error": None,
            })

    # No PIN required or valid session — redirect to assessment
    return RedirectResponse(f"/participate/{problem_id}/{token}/assess", status_code=303)


class PinVerifyRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=4)


@router.post("/api/v1/participate/{problem_id}/{token}/verify-pin")
@limiter.limit("5/15minutes")
async def verify_pin_api(request: Request, problem_id: str, token: str, body: PinVerifyRequest, response: Response):
    problem, user_id = await _find_problem_by_participant_token(problem_id, token)
    if not problem:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    participant = get_participant_by_token(problem, token)
    if not participant:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    success, locked = verify_participant_pin(participant, body.pin)
    await save_problem(user_id, problem)  # Save updated attempts

    if locked:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")
    if not success:
        raise HTTPException(status_code=401, detail="Invalid PIN")

    set_participant_cookie(response, problem_id, participant["id"], token)
    return {"message": "PIN verified", "redirect": f"/participate/{problem_id}/{token}/assess"}


@router.get("/participate/{problem_id}/{token}/assess", response_class=HTMLResponse)
async def participate_assess_page(request: Request, problem_id: str, token: str):
    problem, user_id = await _find_problem_by_participant_token(problem_id, token)
    if not problem:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    participant = get_participant_by_token(problem, token)
    if not participant:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    # Verify PIN session if needed
    if participant.get("pinHash"):
        session = await get_participant_session(request, problem_id)
        if not session or session.get("participantId") != participant["id"]:
            return RedirectResponse(f"/participate/{problem_id}/{token}")

    current_round = problem.get("currentRound", 1)
    assessment = get_assessment(problem, current_round, participant["id"])
    completed, total = count_completed_cells(problem, current_round, participant["id"])

    return templates.TemplateResponse("participate_assess.html", {
        "request": request,
        "problem": problem,
        "participant": participant,
        "assessment": assessment,
        "completed": completed,
        "total": total,
        "round_open": is_round_open(problem),
    })


@router.put("/api/v1/participate/{problem_id}/{token}")
async def submit_assessment(request: Request, problem_id: str, token: str, body: dict):
    problem, user_id = await _find_problem_by_participant_token(problem_id, token)
    if not problem:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    participant = get_participant_by_token(problem, token)
    if not participant:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    if not is_round_open(problem):
        raise HTTPException(status_code=400, detail="Round is closed")

    # Verify PIN session if needed
    if participant.get("pinHash"):
        session = await get_participant_session(request, problem_id)
        if not session or session.get("participantId") != participant["id"]:
            raise HTTPException(status_code=401, detail="PIN verification required")

    current_round = problem.get("currentRound", 1)
    cells = body.get("cells", {})
    submit = body.get("submit", False)

    save_assessment(problem, current_round, participant["id"], cells)

    if submit:
        update_participant_status(problem, participant["id"], "submitted")
    else:
        update_participant_status(problem, participant["id"], "in_progress")

    await save_problem(user_id, problem)

    status = "submitted" if submit else "saved"
    return {"message": f"Assessment {status}", "status": status}


@router.get("/participate/{problem_id}/{token}/done", response_class=HTMLResponse)
async def participate_done_page(request: Request, problem_id: str, token: str):
    problem, user_id = await _find_problem_by_participant_token(problem_id, token)
    if not problem:
        raise HTTPException(status_code=404, detail="Invalid participation link")

    participant = get_participant_by_token(problem, token)

    return templates.TemplateResponse("participate_done.html", {
        "request": request,
        "problem": problem,
        "participant": participant,
        "round_open": is_round_open(problem),
        "problem_id": problem_id,
        "token": token,
    })


# --- Helper ---

async def _find_problem_by_participant_token(problem_id: str, token: str) -> tuple[dict | None, str | None]:
    """Search across all users to find a problem with a matching participant token.

    Returns (problem, user_id) or (None, None).
    """
    # List all user directories
    keys = await storage.list_keys("users/")
    user_ids = set()
    for key in keys:
        parts = key.split("/")
        if len(parts) >= 2:
            user_ids.add(parts[1])

    for uid in user_ids:
        problem = await get_problem(uid, problem_id)
        if problem and problem.get("problemId") == problem_id:
            # Verify token exists
            if get_participant_by_token(problem, token):
                return problem, uid

    return None, None
