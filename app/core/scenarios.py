"""Axis, scenario, and alternative management helpers."""

from typing import Any

MAX_ALTERNATIVES = 8


def update_axes(problem: dict, axes_data: dict) -> dict:
    """Update the axes on a problem. Returns the modified problem."""
    for axis_key in ("x", "y"):
        if axis_key in axes_data:
            ax = axes_data[axis_key]
            problem["axes"][axis_key]["label"] = ax.get("label", problem["axes"][axis_key]["label"])
            for pole in ("lowPole", "highPole"):
                if pole in ax:
                    problem["axes"][axis_key][pole]["label"] = ax[pole].get(
                        "label", problem["axes"][axis_key][pole]["label"]
                    )
                    problem["axes"][axis_key][pole]["description"] = ax[pole].get(
                        "description", problem["axes"][axis_key][pole]["description"]
                    )
    return problem


def update_scenario(problem: dict, scenario_id: str, name: str | None = None, narrative: str | None = None) -> dict:
    """Update a scenario's name and/or narrative."""
    for s in problem["scenarios"]:
        if s["id"] == scenario_id:
            if name is not None:
                s["name"] = name
            if narrative is not None:
                s["narrative"] = narrative
            break
    return problem


def add_alternative(problem: dict, name: str, description: str = "") -> dict | None:
    """Add an alternative. Returns None if max reached."""
    if len(problem["alternatives"]) >= MAX_ALTERNATIVES:
        return None
    # Generate next ID: A, B, C, ...
    used_ids = {a["id"] for a in problem["alternatives"]}
    for c in "ABCDEFGH":
        if c not in used_ids:
            new_id = c
            break
    else:
        return None

    problem["alternatives"].append({
        "id": new_id,
        "name": name,
        "description": description,
    })
    return problem


def update_alternative(problem: dict, alt_id: str, name: str | None = None, description: str | None = None) -> dict:
    """Update an alternative's name/description."""
    for a in problem["alternatives"]:
        if a["id"] == alt_id:
            if name is not None:
                a["name"] = name
            if description is not None:
                a["description"] = description
            break
    return problem


def remove_alternative(problem: dict, alt_id: str) -> dict:
    """Remove an alternative and its assessments."""
    problem["alternatives"] = [a for a in problem["alternatives"] if a["id"] != alt_id]
    # Clean assessments referencing this alternative
    for round_key, round_data in problem.get("assessments", {}).items():
        for participant_id, cells in round_data.items():
            keys_to_remove = [k for k in cells if k.startswith(f"{alt_id}_")]
            for k in keys_to_remove:
                del cells[k]
    return problem


def reorder_alternatives(problem: dict, ordered_ids: list[str]) -> dict:
    """Reorder alternatives by a list of IDs."""
    id_to_alt = {a["id"]: a for a in problem["alternatives"]}
    reordered = [id_to_alt[aid] for aid in ordered_ids if aid in id_to_alt]
    # Append any that weren't in the list (safety)
    remaining = [a for a in problem["alternatives"] if a["id"] not in set(ordered_ids)]
    problem["alternatives"] = reordered + remaining
    return problem
