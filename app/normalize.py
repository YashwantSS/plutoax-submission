import re

_WS = re.compile(r"\s+")


_MONTH_PREFIX = {
    "jan": "Jan",
    "feb": "Feb",
    "mar": "Mar",
    "apr": "Apr",
    "may": "May",
    "jun": "Jun",
    "jul": "Jul",
    "aug": "Aug",
    "sep": "Sep",
    "oct": "Oct",
    "nov": "Nov",
    "dec": "Dec",
}


def normalize_month(raw: str) -> str:
    """Normalize e.g. 'Mar 23', 'mar-23' -> 'Mar-23'."""
    s = _WS.sub(" ", raw.strip())
    m = re.match(
        r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December)[\s/-]+(\d{2})$",
        s,
        re.I,
    )
    if not m:
        return s
    key = m.group(1).lower()[:3]
    abbr = _MONTH_PREFIX.get(key, m.group(1).title()[:3])
    return f"{abbr}-{m.group(2)}"


def normalize_area(raw: str) -> str:
    return _WS.sub(" ", raw.strip())


def normalize_reference(raw: str) -> str:
    s = _WS.sub(" ", raw.strip())
    if s.lower() in ("executed bmr", "executed bmrs"):
        return "Executed BMRs"
    if s.lower() in ("executed bpr", "executed bprs"):
        return "Executed BPRs"
    return s
