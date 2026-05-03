from app.extract import parse_section_text


def sample_section() -> str:
    return """
6.1 Review of Temperature, Relative Humidity and Differential Pressure:
Month Area Reference documents OBSERVED VALUES
Temperature Relative humidity Differential pressure
Limit : NMT 25°C Limit : NMT 60 % RH Limit : NLT 1.5 mm of Wc
Min. Max. Min. Max. Min. Max.
Mar-23 Blender III Executed BMRs 19.5 23.1 15.6 25.1 2.0 2.4
Mar-23 Tablet Inspection
III Executed BMRs 21.8 22.2 55.0 57.0 3.0 3.0
Mar-23 Bulk Packing I Executed BPRs 20.1 20.7 50.4 51.2 2.2 2.2
Jun-23 Bottle Filling and Capping- II Executed BPRs 19.1 20.4 54.3 57.8 27 34
"""


def test_parse_bmr_rows_only_when_filtered():
    rows = parse_section_text(sample_section())
    bmrs = [r for r in rows if r.reference_document == "Executed BMRs"]
    assert len(bmrs) == 2
    by_area = {r.area: r for r in bmrs}
    assert "Blender III" in by_area
    assert by_area["Blender III"].temp_min == 19.5
    assert by_area["Blender III"].dp_max == 2.4
    assert "Tablet Inspection III" in by_area
    assert by_area["Tablet Inspection III"].rh_max == 57.0


def test_bpr_rows_parsed():
    rows = parse_section_text(sample_section())
    bprs = [r for r in rows if r.reference_document == "Executed BPRs"]
    assert len(bprs) == 2


def test_month_glue_no_space_after_year():
    text = """
6.1 Review of Temperature
Mar-23Blender III Executed BMRs 19.5 23.1 15.6 25.1 2.0 2.4
"""
    rows = parse_section_text(text)
    assert len(rows) == 1
    assert rows[0].area == "Blender III"
