"""Small validation helpers; expand after inspecting the real schema."""
from __future__ import annotations

def require_columns(frame, columns):
    """Raise a helpful error if a tabular dataset lacks required columns."""
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
