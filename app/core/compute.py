"""Robustness ranking, fragility index, and aggregation computations."""

import numpy as np
from typing import Any


def compute_robustness(assessments: dict[str, dict], alternatives: list[dict], scenarios: list[dict]) -> list[dict]:
    """Compute robustness ranking from a single participant's assessment or aggregated scores.

    Args:
        assessments: {cellKey: {"score": int, "rationale": str}, ...}
        alternatives: list of alternative dicts with "id" and "name"
        scenarios: list of scenario dicts with "id" and "name"

    Returns:
        Sorted list of dicts: [{"id", "name", "meanScore", "fragility", "scores": {scenarioId: score}}]
    """
    results = []
    for alt in alternatives:
        scores = {}
        score_values = []
        for scen in scenarios:
            cell_key = f"{alt['id']}_{scen['id']}"
            cell = assessments.get(cell_key, {})
            score = cell.get("score")
            if score is not None:
                scores[scen["id"]] = float(score)
                score_values.append(float(score))
            else:
                scores[scen["id"]] = None

        if score_values:
            mean_score = float(np.mean(score_values))
            fragility = float(np.std(score_values, ddof=0))
        else:
            mean_score = 0.0
            fragility = 0.0

        results.append({
            "id": alt["id"],
            "name": alt["name"],
            "meanScore": round(mean_score, 2),
            "fragility": round(fragility, 2),
            "scores": scores,
        })

    # Sort by meanScore descending, then fragility ascending (more robust first)
    results.sort(key=lambda x: (-x["meanScore"], x["fragility"]))
    return results


def aggregate_assessments(
    all_assessments: dict[str, dict],
    alternatives: list[dict],
    scenarios: list[dict],
) -> dict[str, dict]:
    """Aggregate multiple participants' assessments using median.

    Args:
        all_assessments: {participantId: {cellKey: {"score": int}, ...}, ...}

    Returns:
        Aggregated assessment: {cellKey: {"score": float, "mean": float, "median": float, "iqr": float, "n": int}}
    """
    # Collect scores per cell
    cell_scores: dict[str, list[float]] = {}
    for alt in alternatives:
        for scen in scenarios:
            cell_key = f"{alt['id']}_{scen['id']}"
            cell_scores[cell_key] = []

    for participant_id, assessment in all_assessments.items():
        for cell_key, cell_data in assessment.items():
            score = cell_data.get("score")
            if score is not None and cell_key in cell_scores:
                cell_scores[cell_key].append(float(score))

    # Compute aggregates
    result = {}
    for cell_key, scores in cell_scores.items():
        if scores:
            arr = np.array(scores)
            q75, q25 = np.percentile(arr, [75, 25])
            result[cell_key] = {
                "score": float(np.median(arr)),
                "mean": round(float(np.mean(arr)), 2),
                "median": float(np.median(arr)),
                "iqr": round(float(q75 - q25), 2),
                "n": len(scores),
            }
        else:
            result[cell_key] = {"score": None, "mean": None, "median": None, "iqr": None, "n": 0}

    return result


def get_agreement_level(iqr: float | None) -> str:
    """Interpret IQR as agreement level."""
    if iqr is None:
        return "no data"
    if iqr <= 1:
        return "strong"
    if iqr <= 2:
        return "moderate"
    return "divergent"
