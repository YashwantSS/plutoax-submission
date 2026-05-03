# env-table-agent

Python **Stack A** service: ingest PQR-style PDFs, extract **Section 6.1** environmental monitoring rows (temperature, relative humidity, differential pressure), keep only **Executed BMRs** (configurable), store in **SQLite**, and expose **FastAPI** plus a small **natural-language query** helper.

## Setup

```bash
cd env-table-agent
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Three-agent pipeline (recommended)

Runs **extract → validate → analyze** in one flow (no month/area query required for summaries).

| Step | Agent | What it does |
|------|--------|----------------|
| 1 | **Extract** | PDF → environmental rows (same heuristics as before); rows stored in SQLite. |
| 2 | **Validate** | Per-row checks: min≤max, temp NMT 25 °C, RH NMT 60 %, DP NLT 1.5 mm WC (see `app/agents/validate_agent.py`). |
| 3 | **Analyze** | For `Executed BMRs` (configurable), groups by **month** and computes **mean / median / mode** of midpoint `(min+max)/2` for temperature, RH, and differential pressure. |

Endpoints:

- **`POST /v1/pipeline/full`** — multipart `file` + optional query `reference_document` (default `Executed BMRs`). Returns `FullPipelineResult` JSON and persists a `pipeline_runs` snapshot.
- **`POST /v1/pipeline/reprocess`** — JSON `{ "document_id", "reference_document"? }` re-runs validate + analyze on stored rows (after a plain `POST /v1/documents` upload, for example).
- **`GET /v1/documents/{document_id}/pipeline/latest`** — last pipeline snapshot for that document.

Legacy point lookups (optional):

- `POST /v1/documents` — multipart upload `file` (PDF); returns `document_id` and `rows_ingested`.
- `GET /v1/documents/{document_id}/readings` — query params: `month` (e.g. `Mar-23`), `area` (e.g. `Compression IV`), optional `reference_document` (default `Executed BMRs`). If you see **404**, check `rows_ingested` from the upload response, then open **`GET /v1/documents/{document_id}/rows`** to see extracted `month` / `area` / `reference_document` strings (they must match the query exactly).
- `POST /v1/query` — JSON `{ "document_id", "question" }`; crude keyword parser for demos.

## CLI

```bash
python -m app.cli ingest path/to/file.pdf
python -m app.cli pipeline path/to/file.pdf
python -m app.cli query --doc <uuid> --month Mar-23 --area "Compression IV"
```

## Extraction model

1. Extract page text with **pdfplumber**.
2. Locate the block after **6.1** / **OBSERVED VALUES** (or similar) through the next major section header.
3. Parse rows with a **line-oriented state machine**: `Mon-YY` starts a row; area may span lines; `Executed BMRs` / `Executed BPRs` terminates area and precedes six numbers (temp min/max, RH min/max, DP min/max).

Templates differ; adjust `app/extract.py` section anchors if your PDF uses different headings.

## Configuration

Environment variables (optional):

| Variable | Default | Meaning |
|----------|---------|---------|
| `ENV_AGENT_DB_PATH` | `./data/env_agent.db` | SQLite path |
| `ENV_AGENT_UPLOAD_DIR` | `./uploads` | Stored PDF copies |

## Tests

```bash
pytest -q
```
