from __future__ import annotations

import re

from app import database as db
from app.models import QueryAnswer
from app.normalize import normalize_area, normalize_month

_MONTH_IN_TEXT = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December)[\s/-]+(\d{2})\b",
    re.I,
)
_NOISE = re.compile(
    r"(?i)\b(what|was|were|the|a|an|give|show|tell|me|about|reading|readings|values?|value|"
    r"humidity|relative|temperature|temp|differential|pressure|dp|rh|for|in|during|at|"
    r"executed|bmrs|bmr)\b|[?.,!]"
)


def parse_month_area(question: str) -> tuple[str | None, str | None]:
    m = _MONTH_IN_TEXT.search(question)
    if not m:
        return None, None
    month = normalize_month(f"{m.group(1)}-{m.group(2)}")
    tail = question[m.end() :]
    tail = _NOISE.sub(" ", tail)
    area = normalize_area(tail)
    return month, area or None


def answer_question(document_id: str, question: str) -> QueryAnswer:
    month, area_guess = parse_month_area(question)
    if not month:
        return QueryAnswer(
            document_id=document_id,
            message="Could not detect a month (e.g. Mar-23) in the question.",
        )
    if not area_guess:
        return QueryAnswer(
            document_id=document_id,
            month=month,
            message="Could not detect an area name after the month; try rephrasing.",
        )

    reading = db.fetch_reading(document_id, month, area_guess, "Executed BMRs")
    if reading:
        return QueryAnswer(
            document_id=document_id,
            month=month,
            area=reading.area,
            reference_document="Executed BMRs",
            reading=reading,
        )

    reading = db.fetch_reading_fuzzy_area(document_id, month, area_guess, "Executed BMRs")
    if reading:
        return QueryAnswer(
            document_id=document_id,
            month=month,
            area=reading.area,
            reference_document="Executed BMRs",
            reading=reading,
            message="Matched area by partial name.",
        )

    return QueryAnswer(
        document_id=document_id,
        month=month,
        area=area_guess,
        reference_document="Executed BMRs",
        message="No Executed BMRs row for that month and area.",
    )
