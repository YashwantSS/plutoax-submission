from __future__ import annotations

import uuid
from dataclasses import asdict

from app import database as db
from app.agents.analyze_agent import AnalyzeAgentResult, run_analyze_agent
from app.agents.extract_agent import run_extract_agent
from app.agents.validate_agent import ValidateAgentResult, run_validate_agent
from app.extract import RawRow
from app.models import (
    AnalyzePhaseResult,
    ExtractPhaseResult,
    FullPipelineResult,
    MonthMidpointStatsModel,
    ValidatePhaseResult,
    ValidationIssueItem,
)
from app.settings import settings


def run_validate_analyze_for_document(
    document_id: str,
    reference_document: str = "Executed BMRs",
) -> tuple[ValidateAgentResult, AnalyzeAgentResult]:
    rows = _rows_from_db(document_id)
    validate = run_validate_agent(rows)
    analyze = run_analyze_agent(rows, reference_document=reference_document)
    return validate, analyze


def _rows_from_db(document_id: str) -> list[RawRow]:
    readings = db.list_readings(document_id)
    out: list[RawRow] = []
    for r in readings:
        out.append(
            RawRow(
                month=r.month,
                area=r.area,
                reference_document=r.reference_document,
                temp_min=r.temperature_c["min"],
                temp_max=r.temperature_c["max"],
                rh_min=r.relative_humidity_pct["min"],
                rh_max=r.relative_humidity_pct["max"],
                dp_min=r.differential_pressure_mm_wc["min"],
                dp_max=r.differential_pressure_mm_wc["max"],
                page=r.page,
            )
        )
    return out


def _serialize_phases(validate: ValidateAgentResult, analyze: AnalyzeAgentResult) -> tuple[str, str]:
    v_model = ValidatePhaseResult(
        rows_checked=validate.rows_checked,
        rows_valid=validate.rows_valid,
        rows_invalid=validate.rows_invalid,
        issues=[ValidationIssueItem(**asdict(i)) for i in validate.issues],
    )
    a_model = AnalyzePhaseResult(
        reference_document=analyze.reference_document,
        monthly=[MonthMidpointStatsModel(**asdict(m)) for m in analyze.monthly],
    )
    return v_model.model_dump_json(), a_model.model_dump_json()


def build_full_pipeline_result(
    document_id: str,
    stored_path: str,
    extract_row_count: int,
    validate: ValidateAgentResult,
    analyze: AnalyzeAgentResult,
) -> FullPipelineResult:
    return FullPipelineResult(
        document_id=document_id,
        extract=ExtractPhaseResult(rows_extracted=extract_row_count, stored_path=stored_path),
        validate=ValidatePhaseResult(
            rows_checked=validate.rows_checked,
            rows_valid=validate.rows_valid,
            rows_invalid=validate.rows_invalid,
            issues=[ValidationIssueItem(**asdict(i)) for i in validate.issues],
        ),
        analyze=AnalyzePhaseResult(
            reference_document=analyze.reference_document,
            monthly=[MonthMidpointStatsModel(**asdict(m)) for m in analyze.monthly],
        ),
    )


def run_full_pipeline(
    file_bytes: bytes,
    original_name: str | None,
    reference_document: str = "Executed BMRs",
) -> FullPipelineResult:
    """Persist PDF + rows, then run validate and analyze agents."""
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    dest = settings.upload_dir / f"{doc_id}.pdf"
    dest.write_bytes(file_bytes)
    db.insert_document(doc_id, dest, original_name)

    extract = run_extract_agent(str(dest))
    db.replace_readings(doc_id, extract.rows)

    validate = run_validate_agent(extract.rows)
    analyze = run_analyze_agent(extract.rows, reference_document=reference_document)

    v_json, a_json = _serialize_phases(validate, analyze)
    db.insert_pipeline_run(doc_id, str(dest), extract.rows_extracted, v_json, a_json)

    return build_full_pipeline_result(
        doc_id,
        str(dest),
        extract.rows_extracted,
        validate,
        analyze,
    )


def run_reprocess_pipeline(
    document_id: str,
    reference_document: str = "Executed BMRs",
) -> FullPipelineResult:
    stored = db.get_document_stored_path(document_id)
    if not stored:
        raise ValueError("document not found")
    validate, analyze = run_validate_analyze_for_document(document_id, reference_document)
    count = db.count_readings(document_id)
    v_json, a_json = _serialize_phases(validate, analyze)
    db.insert_pipeline_run(document_id, stored, count, v_json, a_json)
    return build_full_pipeline_result(document_id, stored, count, validate, analyze)


def load_latest_pipeline_result(document_id: str) -> FullPipelineResult | None:
    row = db.fetch_latest_pipeline_run(document_id)
    if row is None:
        return None
    return FullPipelineResult(
        document_id=document_id,
        extract=ExtractPhaseResult(
            rows_extracted=int(row["extract_row_count"]),
            stored_path=str(row["stored_path"]),
        ),
        validate=ValidatePhaseResult.model_validate_json(row["validation_json"]),
        analyze=AnalyzePhaseResult.model_validate_json(row["analysis_json"]),
    )
