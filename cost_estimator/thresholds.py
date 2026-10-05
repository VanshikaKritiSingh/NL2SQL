"""M10 threshold configuration loader.

Thresholds live in config/thresholds.json, NOT in code. Every decision in the
decision engine reads from a Thresholds instance. Values ship as placeholders
and MUST be calibrated on real workload (M12/M3) execution telemetry before
production use.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

# Defaults mirror config/thresholds.json; they exist only so the loader never
# crashes when the file is absent. They are PLACEHOLDERS, not tuned values.
DEFAULT_THRESHOLDS: Dict[str, int] = {
    # READ
    "escalate_cost": 50_000,
    "reject_cost": 1_000_000,
    "escalate_rows_scanned": 1_000_000,
    "reject_rows_scanned": 20_000_000,
    "full_scan_min_table_rows": 100_000,
    # WRITE
    "escalate_rows_affected": 100,
    # DDL
    "escalate_table_rows": 500_000,
    # runtime
    "explain_timeout_ms": 2_000,
}


class ThresholdsError(ValueError):
    """Raised when the threshold file is malformed or has invalid values."""


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Immutable threshold set. All values are positive integers."""

    escalate_cost: int
    reject_cost: int
    escalate_rows_scanned: int
    reject_rows_scanned: int
    full_scan_min_table_rows: int
    escalate_rows_affected: int
    escalate_table_rows: int
    explain_timeout_ms: int

    def as_dict(self) -> Dict[str, int]:
        return asdict(self)

    @classmethod
    def defaults(cls) -> "Thresholds":
        return cls.from_values(DEFAULT_THRESHOLDS)

    @classmethod
    def from_values(cls, values: Dict[str, int]) -> "Thresholds":
        merged = {**DEFAULT_THRESHOLDS, **values}
        for key, val in merged.items():
            if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
                raise ThresholdsError(
                    f"threshold {key!r} must be a positive integer, got {val!r}"
                )
        return cls(**merged)


def load_thresholds(path: str | os.PathLike = "config/thresholds.json") -> Thresholds:
    """Load and validate thresholds from a JSON file.

    Missing file -> defaults (with a warning-free load; callers wanting strict
    behaviour can check existence themselves). Malformed file -> ThresholdsError.
    """
    p = Path(path)
    if not p.exists():
        return Thresholds.defaults()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except json.JSONDecodeError as exc:
        raise ThresholdsError(f"{p}: not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ThresholdsError(f"{p}: top-level JSON must be an object")
    return Thresholds.from_values({k: int(v) for k, v in data.items()})
