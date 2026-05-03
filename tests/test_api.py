import importlib


def test_upload_and_query(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV_AGENT_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("ENV_AGENT_UPLOAD_DIR", str(tmp_path / "up"))
    import app.settings as app_settings

    importlib.reload(app_settings)
    import app.database as database

    importlib.reload(database)
    import app.pipeline as pipeline

    importlib.reload(pipeline)
    import app.main as main

    importlib.reload(main)
    from fastapi.testclient import TestClient

    database.init_db()
    monkeypatch.setattr(pipeline, "extract_from_pdf", lambda _path: [])

    client = TestClient(main.app)
    pdf_bytes = b"%PDF-1.4 fake-bytes-not-parsed"
    r = client.post(
        "/v1/documents",
        files={"file": ("demo.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    doc_id = r.json()["document_id"]

    # Synthetic rows would be zero for minimal PDF; still smoke-test endpoints
    q = client.post(
        "/v1/query",
        json={"document_id": doc_id, "question": "Mar-23 Blender III"},
    )
    assert q.status_code == 200
