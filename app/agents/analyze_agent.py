from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean, median, multimode

from app.extract import RawRow


@dataclass(frozen=True)
class MonthMidpointStats:
    month: str
    reference_document: str
    sample_count: int
    mean_of_midpoint_temp_c: float
    median_of_midpoint_temp_c: float
    mode_of_midpoint_temp_c: list[float]
    mean_of_midpoint_rh_pct: float
    median_of_midpoint_rh_pct: float
    mode_of_midpoint_rh_pct: list[float]
    mean_of_midpoint_dp_mm_wc: float
    median_of_midpoint_dp_mm_wc: float
    mode_of_midpoint_dp_mm_wc: list[float]


@dataclass(frozen=True)
class AnalyzeAgentResult:
    """Aggregate min/max midpoints per calendar month label in the data."""

    reference_document: str
    monthly: list[MonthMidpointStats]


def _mid(a: float, b: float) -> float:
    return (a + b) / 2.0


def _modes_rounded(values: list[float], ndigits: int = 2) -> list[float]:
    if not values:
        return []
    rounded = [round(v, ndigits) for v in values]
    modes = multimode(rounded)
    return sorted(set(modes))


def run_analyze_agent(rows: list[RawRow], reference_document: str = "Executed BMRs") -> AnalyzeAgentResult:
    filtered = [r for r in rows if r.reference_document == reference_document]
    by_month: dict[str, list[RawRow]] = {}
    for r in filtered:
        by_month.setdefault(r.month, []).append(r)

    monthly: list[MonthMidpointStats] = []
    for month in sorted(by_month.keys(), key=_month_sort_key):
        group = by_month[month]
        temps = [_mid(r.temp_min, r.temp_max) for r in group]
        rhs = [_mid(r.rh_min, r.rh_max) for r in group]
        dps = [_mid(r.dp_min, r.dp_max) for r in group]
        monthly.append(
            MonthMidpointStats(
                month=month,
                reference_document=reference_document,
                sample_count=len(group),
                mean_of_midpoint_temp_c=round(mean(temps), 4) if temps else 0.0,
                median_of_midpoint_temp_c=round(median(temps), 4) if temps else 0.0,
                mode_of_midpoint_temp_c=_modes_rounded(temps),
                mean_of_midpoint_rh_pct=round(mean(rhs), 4) if rhs else 0.0,
                median_of_midpoint_rh_pct=round(median(rhs), 4) if rhs else 0.0,
                mode_of_midpoint_rh_pct=_modes_rounded(rhs),
                mean_of_midpoint_dp_mm_wc=round(mean(dps), 4) if dps else 0.0,
                median_of_midpoint_dp_mm_wc=round(median(dps), 4) if dps else 0.0,
                mode_of_midpoint_dp_mm_wc=_modes_rounded(dps),
            )
        )
    return AnalyzeAgentResult(reference_document=reference_document, monthly=monthly)


def _month_sort_key(label: str) -> tuple[int, int]:
    """Sort Mon-YY roughly chronologically within a single PQR year window."""
    m = re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2})$", label, re.I)
    if not m:
        return (99, 99)
    order = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    mon = m.group(1).lower()[:3]
    yy = int(m.group(2))
    return (yy, order.get(mon, 0))
