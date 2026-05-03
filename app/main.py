from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from app import database as db
from app.agent_query import answer_question
from app.agents.orchestrator import load_latest_pipeline_result, run_full_pipeline, run_reprocess_pipeline
from app.models import (
    DocumentIngestResult,
    DocumentRowsSummary,
    EnvReading,
    FullPipelineResult,
    QueryAnswer,
    QueryBody,
    ReprocessBody,
)
from app.pipeline import ingest_pdf

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="env-table-agent", version="0.1.0", lifespan=lifespan)


@app.post("/v1/documents", response_model=DocumentIngestResult)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Expected a PDF file.")
    raw = await file.read()
    return ingest_pdf(raw, file.filename)


@app.post("/v1/pipeline/full", response_model=FullPipelineResult)
async def pipeline_full(
    file: UploadFile = File(...),
    reference_document: str = Query(
        "Executed BMRs",
        description="Analyze agent only aggregates rows with this reference (e.g. Executed BMRs).",
    ),
):
    """Run three agents in order: extract PDF → validate rows → monthly analysis (mean/median/mode)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Expected a PDF file.")
    raw = await file.read()
    return run_full_pipeline(raw, file.filename, reference_document=reference_document)


@app.post("/v1/pipeline/reprocess", response_model=FullPipelineResult)
def pipeline_reprocess(body: ReprocessBody):
    """Re-run validate + analyze on rows already stored for document_id (no re-ingest)."""
    try:
        return run_reprocess_pipeline(body.document_id, body.reference_document)
    except ValueError:
        raise HTTPException(status_code=404, detail="document not found")


@app.get("/v1/documents/{document_id}/pipeline/latest", response_model=FullPipelineResult)
def pipeline_latest(document_id: str):
    """Return the most recent three-agent pipeline snapshot for this document."""
    r = load_latest_pipeline_result(document_id)
    if r is None:
        raise HTTPException(
            status_code=404,
            detail="No pipeline run found. Upload via POST /v1/pipeline/full or reprocess via POST /v1/pipeline/reprocess.",
        )
    return r


@app.get("/v1/documents/{document_id}/rows", response_model=DocumentRowsSummary)
def list_document_rows(document_id: str):
    """Debug: see what was extracted for this upload (month/area/ref must match these for GET readings)."""
    rows = db.list_readings(document_id)
    return DocumentRowsSummary(document_id=document_id, row_count=len(rows), rows=rows)


@app.get("/v1/documents/{document_id}/readings", response_model=EnvReading | None)
def get_readings(
    document_id: str,
    month: str = Query(..., description="e.g. Mar-23"),
    area: str = Query(..., description="e.g. Compression IV"),
    reference_document: str = Query("Executed BMRs"),
):
    reading = db.fetch_reading(document_id, month, area, reference_document)
    if reading is None:
        total = db.count_readings(document_id)
        if total == 0:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Reading not found.",
                    "reason": "No environmental rows were stored for this document_id. "
                    "Extraction likely found no matching table text (wrong template, image-only PDF, or headings differ).",
                    "rows_for_document": 0,
                    "hint": "Check POST /v1/documents response field rows_ingested. If 0, open GET /v1/documents/{id}/rows and adjust app/extract.py anchors.",
                },
            )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Reading not found.",
                "reason": "There are stored rows, but none match this month, area, and reference_document.",
                "rows_for_document": total,
                "hint": "Call GET /v1/documents/{id}/rows and copy exact month, area, and reference_document values.",
                "query": {"month": month, "area": area, "reference_document": reference_document},
            },
        )
    return reading


@app.post("/v1/query", response_model=QueryAnswer)
def post_query(body: QueryBody):
    return answer_question(body.document_id, body.question)
