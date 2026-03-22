"""Impact assessment storage and retrieval."""

from typing import Any


def get_round_key(round_number: int) -> str:
    return f"round_{round_number}"


def get_assessment(problem: dict, round_number: int, participant_id: str) -> dict:
    """Get a participant's assessment for a round. Returns empty dict if none."""
    round_key = get_round_key(round_number)
    return problem.get("assessments", {}).get(round_key, {}).get(participant_id, {})


def save_assessment(
    problem: dict,
    round_number: int,
    participant_id: str,
    cells: dict[str, dict],
) -> dict:
    """Save (merge) a participant's assessment cells for a round.

    cells format: {"A_Q1": {"score": 4, "rationale": "..."}, ...}
    Returns the modified problem.
    """
    round_key = get_round_key(round_number)

    if "assessments" not in problem:
        problem["assessments"] = {}
    if round_key not in problem["assessments"]:
        problem["assessments"][round_key] = {}
    if participant_id not in problem["assessments"][round_key]:
        problem["assessments"][round_key][participant_id] = {}

    existing = problem["assessments"][round_key][participant_id]

    for cell_key, cell_data in cells.items():
        # Validate cell key format: {altId}_{scenarioId}
        parts = cell_key.split("_")
        if len(parts) != 2:
            continue
        alt_id, scenario_id = parts
        valid_alts = {a["id"] for a in problem.get("alternatives", [])}
        valid_scenarios = {s["id"] for s in problem.get("scenarios", [])}
        if alt_id not in valid_alts or scenario_id not in valid_scenarios:
            continue

        # Validate score range
        score = cell_data.get("score")
        if score is not None:
            score = int(score)
            if score < 1 or score > 5:
                continue
            existing[cell_key] = {
                "score": score,
                "rationale": str(cell_data.get("rationale", ""))[:500],
            }

    return problem


def get_all_assessments_for_round(problem: dict, round_number: int) -> dict[str, dict]:
    """Get all participant assessments for a round.

    Returns {participantId: {cellKey: {score, rationale}, ...}, ...}
    """
    round_key = get_round_key(round_number)
    return problem.get("assessments", {}).get(round_key, {})


def count_completed_cells(problem: dict, round_number: int, participant_id: str) -> tuple[int, int]:
    """Return (completed, total) cell count for a participant."""
    assessment = get_assessment(problem, round_number, participant_id)
    total = len(problem.get("alternatives", [])) * len(problem.get("scenarios", []))
    completed = sum(1 for v in assessment.values() if v.get("score") is not None)
    return completed, total
