import importlib

from app.extract import RawRow


def test_insert_and_fetch(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV_AGENT_DB_PATH", str(tmp_path / "d.db"))
    import app.settings as app_settings

    importlib.reload(app_settings)
    import app.database as database

    importlib.reload(database)
    database.init_db()
    doc_id = "test-doc-1"
    database.insert_document(doc_id, tmp_path / "x.pdf", "x.pdf")
    rows = [
        RawRow(
            month="Mar-23",
            area="Compression IV",
            reference_document="Executed BMRs",
            temp_min=20.2,
            temp_max=22.7,
            rh_min=32.9,
            rh_max=38.9,
            dp_min=2.0,
            dp_max=2.2,
            page=2,
        )
    ]
    database.replace_readings(doc_id, rows)
    r = database.fetch_reading(doc_id, "Mar-23", "compression iv", "Executed BMRs")
    assert r is not None
    assert r.temperature_c["min"] == 20.2
    assert r.differential_pressure_mm_wc["max"] == 2.2
