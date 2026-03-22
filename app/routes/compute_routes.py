"""Compute routes: robustness ranking, consensus, aggregation."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.login_manager import get_current_user
from app.core.assessments import get_all_assessments_for_round
from app.core.compute import aggregate_assessments, compute_robustness
from app.core.consensus import compute_consensus
from app.core.problems import get_problem

router = APIRouter()


@router.post("/api/v1/compute/robustness")
async def compute_robustness_api(body: dict, user: dict = Depends(get_current_user)):
    """Compute robustness from provided assessment data."""
    assessments = body.get("assessments", {})
    alternatives = body.get("alternatives", [])
    scenarios = body.get("scenarios", [])
    result = compute_robustness(assessments, alternatives, scenarios)
    return {"ranking": result}


@router.post("/api/v1/compute/consensus")
async def compute_consensus_api(body: dict, user: dict = Depends(get_current_user)):
    """Compute consensus from provided multi-participant assessments."""
    all_assessments = body.get("assessments", {})
    alternatives = body.get("alternatives", [])
    scenarios = body.get("scenarios", [])
    result = compute_consensus(all_assessments, alternatives, scenarios)
    return result


@router.post("/api/v1/compute/aggregate")
async def compute_aggregate_api(body: dict, user: dict = Depends(get_current_user)):
    """Aggregate multi-participant assessments."""
    all_assessments = body.get("assessments", {})
    alternatives = body.get("alternatives", [])
    scenarios = body.get("scenarios", [])
    result = aggregate_assessments(all_assessments, alternatives, scenarios)
    return {"aggregated": result}


@router.get("/api/v1/problems/{problem_id}/consensus")
async def get_problem_consensus(problem_id: str, user: dict = Depends(get_current_user)):
    """Compute consensus for a specific problem's current round."""
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    current_round = problem.get("currentRound", 1)
    all_assessments = get_all_assessments_for_round(problem, current_round)

    if not all_assessments:
        return {"overall": {"W": None, "interpretation": "No assessments submitted"}, "per_scenario": {}}

    alternatives = problem.get("alternatives", [])
    scenarios = problem.get("scenarios", [])

    consensus = compute_consensus(all_assessments, alternatives, scenarios)

    # Also compute aggregated scores and robustness
    aggregated = aggregate_assessments(all_assessments, alternatives, scenarios)
    robustness = compute_robustness(aggregated, alternatives, scenarios)

    return {
        **consensus,
        "aggregated": aggregated,
        "robustness": robustness,
    }
