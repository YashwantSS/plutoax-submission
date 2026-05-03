from __future__ import annotations

from dataclasses import dataclass

from app.extract import RawRow

# PQR-style environmental limits (from template; adjust if your spec differs).
LIMIT_TEMP_MAX_C = 25.0
LIMIT_RH_MAX_PCT = 60.0
LIMIT_DP_MIN_MM_WC = 1.5


@dataclass(frozen=True)
class ValidationIssue:
    row_index: int
    month: str
    area: str
    reference_document: str
    issues: list[str]


@dataclass(frozen=True)
class ValidateAgentResult:
    rows_checked: int
    rows_valid: int
    rows_invalid: int
    issues: list[ValidationIssue]


def _check_row(i: int, r: RawRow) -> list[str]:
    problems: list[str] = []
    if r.temp_min > r.temp_max:
        problems.append("temperature_min_gt_max")
    if r.rh_min > r.rh_max:
        problems.append("rh_min_gt_max")
    if r.dp_min > r.dp_max:
        problems.append("differential_pressure_min_gt_max")
    if r.temp_max > LIMIT_TEMP_MAX_C:
        problems.append("temperature_max_exceeds_NMT_25C")
    if r.rh_max > LIMIT_RH_MAX_PCT:
        problems.append("rh_max_exceeds_NMT_60pct")
    if r.dp_min < LIMIT_DP_MIN_MM_WC:
        problems.append("differential_pressure_min_below_NLT_1_5_mm_WC")
    return problems


def run_validate_agent(rows: list[RawRow]) -> ValidateAgentResult:
    issues: list[ValidationIssue] = []
    invalid = 0
    for i, r in enumerate(rows):
        row_issues = _check_row(i, r)
        if row_issues:
            invalid += 1
            issues.append(
                ValidationIssue(
                    row_index=i,
                    month=r.month,
                    area=r.area,
                    reference_document=r.reference_document,
                    issues=row_issues,
                )
            )
    return ValidateAgentResult(
        rows_checked=len(rows),
        rows_valid=len(rows) - invalid,
        rows_invalid=invalid,
        issues=issues,
    )
