"""Kendall's W (coefficient of concordance) and per-scenario agreement."""

import numpy as np
from scipy import stats
from typing import Any


def compute_kendalls_w(rankings: list[list[float]]) -> dict:
    """Compute Kendall's W coefficient of concordance.

    Args:
        rankings: List of rankings, one per rater. Each ranking is a list of scores
                  corresponding to the same set of items (alternatives).

    Returns:
        {"W": float, "chi2": float, "p_value": float, "n_raters": int, "n_items": int, "interpretation": str}
    """
    if len(rankings) < 2:
        return {
            "W": None,
            "chi2": None,
            "p_value": None,
            "n_raters": len(rankings),
            "n_items": len(rankings[0]) if rankings else 0,
            "interpretation": "Insufficient raters for concordance analysis",
        }

    k = len(rankings)  # number of raters
    n = len(rankings[0])  # number of items

    if n < 2:
        return {
            "W": None, "chi2": None, "p_value": None,
            "n_raters": k, "n_items": n,
            "interpretation": "Insufficient items for concordance analysis",
        }

    # Convert scores to ranks
    ranked = []
    for rater_scores in rankings:
        ranked.append(stats.rankdata(rater_scores))

    ranked_matrix = np.array(ranked)  # k × n

    # Sum of ranks for each item
    rank_sums = ranked_matrix.sum(axis=0)

    # Mean rank sum
    mean_rank_sum = np.mean(rank_sums)

    # S = sum of squared deviations of rank sums from mean
    S = np.sum((rank_sums - mean_rank_sum) ** 2)

    # W = 12 * S / (k^2 * (n^3 - n))
    denominator = k**2 * (n**3 - n)
    if denominator == 0:
        W = 0.0
    else:
        W = (12 * S) / denominator

    # Chi-squared approximation
    chi2 = k * (n - 1) * W
    df = n - 1
    p_value = 1 - stats.chi2.cdf(chi2, df)

    # Interpretation
    if W >= 0.7:
        interpretation = "Strong agreement among raters"
    elif W >= 0.5:
        interpretation = "Moderate agreement among raters"
    elif W >= 0.3:
        interpretation = "Weak agreement among raters"
    else:
        interpretation = "Little to no agreement among raters"

    return {
        "W": round(float(W), 4),
        "chi2": round(float(chi2), 4),
        "p_value": round(float(p_value), 4),
        "n_raters": k,
        "n_items": n,
        "interpretation": interpretation,
    }


def compute_per_scenario_agreement(
    all_assessments: dict[str, dict],
    alternatives: list[dict],
    scenarios: list[dict],
) -> dict[str, dict]:
    """Compute agreement metrics per scenario.

    Returns: {scenarioId: {"W": float, "interpretation": str, "mean_iqr": float}}
    """
    results = {}

    for scen in scenarios:
        # For this scenario, collect each rater's scores across alternatives
        rater_scores = []
        for participant_id, assessment in all_assessments.items():
            scores = []
            for alt in alternatives:
                cell_key = f"{alt['id']}_{scen['id']}"
                cell = assessment.get(cell_key, {})
                score = cell.get("score")
                scores.append(float(score) if score is not None else 3.0)  # default to middle
            rater_scores.append(scores)

        # Compute Kendall's W for this scenario
        if len(rater_scores) >= 2 and len(alternatives) >= 2:
            w_result = compute_kendalls_w(rater_scores)
        else:
            w_result = {"W": None, "interpretation": "Insufficient data"}

        # Compute mean IQR across cells in this scenario
        iqrs = []
        for alt in alternatives:
            cell_key = f"{alt['id']}_{scen['id']}"
            scores = []
            for participant_id, assessment in all_assessments.items():
                cell = assessment.get(cell_key, {})
                s = cell.get("score")
                if s is not None:
                    scores.append(float(s))
            if len(scores) >= 2:
                q75, q25 = np.percentile(scores, [75, 25])
                iqrs.append(q75 - q25)

        mean_iqr = round(float(np.mean(iqrs)), 2) if iqrs else None

        results[scen["id"]] = {
            "W": w_result.get("W"),
            "interpretation": w_result.get("interpretation", ""),
            "mean_iqr": mean_iqr,
        }

    return results


def compute_consensus(
    all_assessments: dict[str, dict],
    alternatives: list[dict],
    scenarios: list[dict],
) -> dict:
    """Full consensus analysis: overall Kendall's W + per-scenario breakdown.

    Returns:
        {
            "overall": {W, chi2, p_value, ...},
            "per_scenario": {scenarioId: {W, interpretation, mean_iqr}},
        }
    """
    # Overall: each rater's robustness ranking (mean score per alternative)
    rater_rankings = []
    for participant_id, assessment in all_assessments.items():
        alt_means = []
        for alt in alternatives:
            scores = []
            for scen in scenarios:
                cell_key = f"{alt['id']}_{scen['id']}"
                cell = assessment.get(cell_key, {})
                s = cell.get("score")
                if s is not None:
                    scores.append(float(s))
            alt_means.append(float(np.mean(scores)) if scores else 0.0)
        rater_rankings.append(alt_means)

    overall = compute_kendalls_w(rater_rankings) if len(rater_rankings) >= 2 else {
        "W": None, "chi2": None, "p_value": None,
        "n_raters": len(rater_rankings),
        "n_items": len(alternatives),
        "interpretation": "Insufficient raters",
    }

    per_scenario = compute_per_scenario_agreement(all_assessments, alternatives, scenarios)

    return {
        "overall": overall,
        "per_scenario": per_scenario,
    }
