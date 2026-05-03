import uuid
from pathlib import Path

from app import database as db
from app.extract import extract_from_pdf
from app.models import DocumentIngestResult
from app.settings import settings


def ingest_pdf(file_bytes: bytes, original_name: str | None) -> DocumentIngestResult:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    dest = settings.upload_dir / f"{doc_id}.pdf"
    dest.write_bytes(file_bytes)
    db.insert_document(doc_id, dest, original_name)

    rows = extract_from_pdf(str(dest))
    n = db.replace_readings(doc_id, rows)
    return DocumentIngestResult(document_id=doc_id, rows_ingested=n, stored_path=str(dest))


def ingest_pdf_path(path: Path, original_name: str | None = None) -> DocumentIngestResult:
    data = path.read_bytes()
    return ingest_pdf(data, original_name or path.name)
