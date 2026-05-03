from __future__ import annotations

from dataclasses import dataclass

from app.extract import RawRow, extract_from_pdf


@dataclass(frozen=True)
class ExtractAgentResult:
    """Output of the extraction agent (PDF → structured rows)."""

    rows: list[RawRow]
    pdf_path: str

    @property
    def rows_extracted(self) -> int:
        return len(self.rows)


def run_extract_agent(pdf_path: str) -> ExtractAgentResult:
    rows = extract_from_pdf(pdf_path)
    return ExtractAgentResult(rows=rows, pdf_path=pdf_path)
