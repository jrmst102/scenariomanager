"""Round lifecycle management: open, close, reopen, new."""

from datetime import datetime, timezone


def get_current_round(problem: dict) -> dict | None:
    """Get the current round object."""
    current = problem.get("currentRound", 1)
    for r in problem.get("rounds", []):
        if r["roundNumber"] == current:
            return r
    return None


def is_round_open(problem: dict) -> bool:
    """Check if the current round is open."""
    r = get_current_round(problem)
    return r is not None and r.get("status") == "open"


def close_round(problem: dict) -> bool:
    """Close the current round. Returns True if successful."""
    r = get_current_round(problem)
    if r is None or r["status"] != "open":
        return False
    r["status"] = "closed"
    r["closedAt"] = datetime.now(timezone.utc).isoformat()
    return True


def reopen_round(problem: dict) -> bool:
    """Reopen the current round. Returns True if successful."""
    r = get_current_round(problem)
    if r is None or r["status"] != "closed":
        return False
    r["status"] = "open"
    r["closedAt"] = None
    return True


def new_round(problem: dict) -> dict:
    """Open a new round. Returns the new round object."""
    # Close current round if open
    current = get_current_round(problem)
    if current and current["status"] == "open":
        close_round(problem)

    new_number = problem.get("currentRound", 1) + 1
    now = datetime.now(timezone.utc).isoformat()
    round_obj = {
        "roundNumber": new_number,
        "status": "open",
        "openedAt": now,
        "closedAt": None,
    }
    problem["rounds"].append(round_obj)
    problem["currentRound"] = new_number

    # Reset participant statuses
    for p in problem.get("participants", []):
        p["status"] = "pending"

    return round_obj


def finalize_problem(problem: dict) -> bool:
    """Finalize a problem (close current round, mark as finalized)."""
    close_round(problem)
    problem["config"]["finalized"] = True
    return True
