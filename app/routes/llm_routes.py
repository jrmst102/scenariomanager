"""LLM routes: report narrative generation."""

from fastapi import APIRouter, Depends, HTTPException

from app.ai.openai_client import check_llm_status, generate_narrative
from app.ai.prompts import build_narrative_prompt
from app.auth.login_manager import get_current_user
from app.core.assessments import get_all_assessments_for_round
from app.core.compute import aggregate_assessments, compute_robustness
from app.core.consensus import compute_consensus
from app.core.problems import get_problem, save_problem

router = APIRouter()

# Track regeneration counts per problem (in-memory, resets on restart)
_regen_counts: dict[str, int] = {}
MAX_REGENERATIONS = 3


@router.get("/api/v1/llm/status")
async def llm_status():
    return await check_llm_status()


@router.post("/api/v1/problems/{problem_id}/report/narrative")
async def generate_report_narrative(problem_id: str, user: dict = Depends(get_current_user)):
    problem = await get_problem(user["userId"], problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Build analysis data
    current_round = problem.get("currentRound", 1)
    all_assessments = get_all_assessments_for_round(problem, current_round)
    alternatives = problem.get("alternatives", [])
    scenarios = problem.get("scenarios", [])

    if all_assessments:
        aggregated = aggregate_assessments(all_assessments, alternatives, scenarios)
        robustness = compute_robustness(aggregated, alternatives, scenarios)
        consensus = compute_consensus(all_assessments, alternatives, scenarios)
    else:
        # Single-user: use owner assessment if available
        owner_assessment = {}
        for pid, assess in get_all_assessments_for_round(problem, current_round).items():
            owner_assessment = assess
            break
        robustness = compute_robustness(owner_assessment, alternatives, scenarios)
        consensus = None

    prompt = build_narrative_prompt(problem, robustness, consensus)
    result = await generate_narrative(prompt)

    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])

    # Save to problem
    problem["report"] = {
        "narrative": result["narrative"],
        "generatedAt": result["generatedAt"],
        "model": result["model"],
    }
    await save_problem(user["userId"], problem)

    # Track regeneration count
    _regen_counts[problem_id] = 1

    return result


@router.post("/api/v1/problems/{problem_id}/report/narrative/regenerate")
async def regenerate_report_narrative(problem_id: str, user: dict = Depends(get_current_user)):
    count = _regen_counts.get(problem_id, 0)
    if count >= MAX_REGENERATIONS:
        raise HTTPException(status_code=429, detail=f"Maximum {MAX_REGENERATIONS} regenerations per session")

    # Reuse the generate logic
    result = await generate_report_narrative(problem_id, user)
    _regen_counts[problem_id] = count + 1
    return result
