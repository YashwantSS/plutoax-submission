from __future__ import annotations

import re
from dataclasses import dataclass

import pdfplumber

from app.normalize import normalize_area, normalize_month, normalize_reference

# No \b after YY: PDF text often glues "Mar-23Blender" with no space/word-boundary.
_MONTH_START = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-/](\d{2})\s*(.*)$",
    re.I,
)
_NUM = re.compile(r"[-+]?\d*\.?\d+")
_REF_BMR = "Executed BMRs"
_REF_BPR = "Executed BPRs"
_MARKERS = (_REF_BMR, _REF_BPR)


def _split_reference(segment: str) -> tuple[str, str, str] | None:
    """Return (left_of_ref, reference, right_numbers) or None."""
    for ref in _MARKERS:
        if ref in segment:
            left, right = segment.split(ref, 1)
            return left.strip(), ref, right.strip()
    return None


def _parse_six_numbers(s: str) -> tuple[float, float, float, float, float, float] | None:
    nums = [float(x) for x in _NUM.findall(s)]
    if len(nums) < 6:
        return None
    return nums[0], nums[1], nums[2], nums[3], nums[4], nums[5]


def _slice_section_text(full_text: str) -> str:
    """Reduce PDF text to the environmental monitoring block when possible."""
    lower = full_text.lower()
    start_keys = (
        "6.1 review of temperature",
        "observed values",
        "6.0 review of temperature",
    )
    start = 0
    for key in start_keys:
        idx = lower.find(key)
        if idx != -1:
            start = idx
            break
    chunk = full_text[start:]
    # Stop before next major numbered section if present
    stop_m = re.search(r"\n\s*7\.0\s+", chunk, re.I)
    if stop_m:
        chunk = chunk[: stop_m.start()]
    return chunk


@dataclass
class RawRow:
    month: str
    area: str
    reference_document: str
    temp_min: float
    temp_max: float
    rh_min: float
    rh_max: float
    dp_min: float
    dp_max: float
    page: int | None = None


def parse_section_text(text: str, page: int | None = None) -> list[RawRow]:
    """Parse environmental-style rows from plain text (one page or section)."""
    section = _slice_section_text(text)
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
    out: list[RawRow] = []
    current_month: str | None = None
    area_parts: list[str] = []

    def emit(left_segment: str, ref: str, nums_tail: str) -> None:
        nonlocal current_month, area_parts
        if current_month is None:
            return
        parts = [*area_parts]
        if left_segment:
            parts.append(left_segment)
        area = normalize_area(" ".join(parts))
        ref_n = normalize_reference(ref)
        parsed = _parse_six_numbers(nums_tail)
        if parsed is None:
            current_month = None
            area_parts = []
            return
        tmin, tmax, rhmin, rhmax, dpmin, dpmax = parsed
        out.append(
            RawRow(
                month=normalize_month(current_month),
                area=area,
                reference_document=ref_n,
                temp_min=tmin,
                temp_max=tmax,
                rh_min=rhmin,
                rh_max=rhmax,
                dp_min=dpmin,
                dp_max=dpmax,
                page=page,
            )
        )
        current_month = None
        area_parts = []

    for line in lines:
        # Skip obvious header / limit lines
        if "Limit :" in line or line.startswith("Min.") and "Max." in line:
            continue
        m = _MONTH_START.match(line)
        if m:
            # flush incomplete
            current_month = f"{m.group(1).title()[:3]}-{m.group(2)}"
            rest = (m.group(3) or "").strip()
            area_parts = []
            sp = _split_reference(rest) if rest else None
            if sp:
                left, ref, right = sp
                emit(left, ref, right)
            elif rest:
                area_parts = [rest]
            continue

        if current_month is None:
            continue

        sp = _split_reference(line)
        if sp:
            left, ref, right = sp
            emit(left, ref, right)
        else:
            area_parts.append(line)

    return out


def extract_from_pdf(path: str) -> list[RawRow]:
    """Extract rows from all pages of a PDF."""
    rows: list[RawRow] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for r in parse_section_text(text, page=i):
                rows.append(r)
    return rows
