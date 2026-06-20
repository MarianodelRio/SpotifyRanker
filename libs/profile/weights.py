from __future__ import annotations


def normalize_sum(raw: dict[str, float]) -> dict[str, float]:
    """Normalize values so they sum to 1.0. Returns {} if all values are zero."""
    total = sum(raw.values())
    if total == 0.0:
        return {}
    return {k: v / total for k, v in raw.items()}


def normalize_max(raw: dict[str, float]) -> dict[str, float]:
    """Normalize values to [0, 1] by dividing by the maximum. Returns {} if empty."""
    if not raw:
        return {}
    max_val = max(raw.values())
    if max_val == 0.0:
        return {k: 0.0 for k in raw}
    return {k: v / max_val for k, v in raw.items()}
