"""Problem CRUD routes and editor pages."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.auth.login_manager import get_current_user
from app.core.problems import (
    create_problem,
    delete_problem,
    get_problem,
    get_problems_index,
    import_problem,
    save_problem,
)
from app.core.scenarios import (
    add_alternative,
    remove_alternative,
    reorder_alternatives,
    update_alternative,
    update_axes,
    update_scenario,
)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))


async def _get_problem_with_retry(
    user_id: str, problem_id: str, retries: int = 3, delay: float = 0.5
) -> dict | None:
    """Get problem with retry to handle storage eventual consistency."""
    for attempt in range(retries):
        problem = await get_problem(user_id, problem_id)
        if problem is not None:
            return problem
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    return None


# --- Page Routes ---

@router.get("/problems", response_class=HTMLResponse)
async def problem_list_page(request: Request, user: dict = Depends(get_current_user)):
    problems = await get_problems_index(user["userId"])
    return templates.TemplateResponse("problem_list.html", {
        "request": request,
        "user": user,
        "problems": problems,
    })


@router.get("/problems/{problem_id}/edit", response_class=HTMLResponse)
async def problem_editor_page(request: Request, problem_id: str, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return templates.TemplateResponse("problem_editor.html", {
        "request": request,
        "user": user,
        "problem": problem,
    })


@router.get("/problems/{problem_id}/assess", response_class=HTMLResponse)
async def assessment_page(request: Request, problem_id: str, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return templates.TemplateResponse("assessment.html", {
        "request": request,
        "user": user,
        "problem": problem,
    })


@router.get("/problems/{problem_id}/results", response_class=HTMLResponse)
async def results_page(request: Request, problem_id: str, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return templates.TemplateResponse("results.html", {
        "request": request,
        "user": user,
        "problem": problem,
    })


@router.get("/problems/{problem_id}/report", response_class=HTMLResponse)
async def report_page(request: Request, problem_id: str, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return templates.TemplateResponse("report.html", {
        "request": request,
        "user": user,
        "problem": problem,
    })


# --- API Routes ---

@router.get("/api/v1/problems")
async def list_problems(user: dict = Depends(get_current_user)):
    return await get_problems_index(user["userId"])


class CreateProblemRequest(BaseModel):
    title: str = ""
    description: str = ""


@router.post("/api/v1/problems")
async def create_problem_api(body: CreateProblemRequest, user: dict = Depends(get_current_user)):
    problem = await create_problem(user["userId"], body.title, body.description)
    return {"problemId": problem["problemId"], "message": "Problem created"}


@router.get("/api/v1/problems/{problem_id}")
async def get_problem_api(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


class UpdateProblemRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    axes: dict | None = None
    scenarios: list[dict] | None = None
    alternatives: list[dict] | None = None


@router.put("/api/v1/problems/{problem_id}")
async def update_problem_api(problem_id: str, body: UpdateProblemRequest, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if body.title is not None:
        problem["title"] = body.title
    if body.description is not None:
        problem["description"] = body.description
    if body.axes is not None:
        problem = update_axes(problem, body.axes)
    if body.scenarios is not None:
        for s in body.scenarios:
            if "id" in s:
                problem = update_scenario(problem, s["id"], s.get("name"), s.get("narrative"))
    if body.alternatives is not None:
        problem["alternatives"] = body.alternatives[:8]  # Enforce max

    await save_problem(user["userId"], problem)
    return {"message": "Problem updated"}


@router.delete("/api/v1/problems/{problem_id}")
async def delete_problem_api(problem_id: str, user: dict = Depends(get_current_user)):
    deleted = await delete_problem(user["userId"], problem_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Problem not found")
    return {"message": "Problem deleted"}


@router.post("/api/v1/problems/{problem_id}/save")
async def save_problem_api(problem_id: str, user: dict = Depends(get_current_user)):
    """Explicit save endpoint (same as PUT but clearer intent)."""
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    await save_problem(user["userId"], problem)
    return {"message": "Problem saved"}


@router.get("/api/v1/problems/{problem_id}/download")
async def download_problem(problem_id: str, user: dict = Depends(get_current_user)):
    """Download problem as .SCN file."""
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    filename = f"{problem.get('title', 'problem').replace(' ', '_')}.SCN"
    return JSONResponse(
        content=problem,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/v1/problems/upload")
async def upload_problem(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload and import a .SCN file."""
    if not file.filename or not file.filename.upper().endswith(".SCN"):
        raise HTTPException(status_code=400, detail="File must have .SCN extension")

    content = await file.read()
    if len(content) > 1_000_000:  # 1MB limit
        raise HTTPException(status_code=400, detail="File too large")

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    problem = await import_problem(user["userId"], data)
    if not problem:
        raise HTTPException(status_code=400, detail="Invalid .SCN file format")

    return {"problemId": problem["problemId"], "message": "Problem imported"}


# --- Alternative management sub-routes ---

class AlternativeRequest(BaseModel):
    name: str
    description: str = ""


@router.post("/api/v1/problems/{problem_id}/alternatives")
async def add_alternative_api(problem_id: str, body: AlternativeRequest, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    result = add_alternative(problem, body.name, body.description)
    if result is None:
        raise HTTPException(status_code=400, detail="Maximum 8 alternatives reached")
    await save_problem(user["userId"], problem)
    return {"message": "Alternative added", "alternatives": problem["alternatives"]}


@router.delete("/api/v1/problems/{problem_id}/alternatives/{alt_id}")
async def remove_alternative_api(problem_id: str, alt_id: str, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    remove_alternative(problem, alt_id)
    await save_problem(user["userId"], problem)
    return {"message": "Alternative removed"}


class ReorderRequest(BaseModel):
    orderedIds: list[str]


@router.put("/api/v1/problems/{problem_id}/alternatives/reorder")
async def reorder_alternatives_api(problem_id: str, body: ReorderRequest, user: dict = Depends(get_current_user)):
    problem = await _get_problem_with_retry(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    reorder_alternatives(problem, body.orderedIds)
    await save_problem(user["userId"], problem)
    return {"message": "Alternatives reordered"}
