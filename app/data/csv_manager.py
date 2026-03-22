"""CSV read/write helpers for user data management."""

import csv
import io
from typing import Any


def dict_list_to_csv(data: list[dict]) -> str:
    """Convert a list of dicts to CSV string."""
    if not data:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def csv_to_dict_list(csv_string: str) -> list[dict]:
    """Parse a CSV string into a list of dicts."""
    reader = csv.DictReader(io.StringIO(csv_string))
    return list(reader)
