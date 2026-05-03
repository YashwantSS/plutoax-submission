from app.agents.analyze_agent import run_analyze_agent
from app.agents.validate_agent import run_validate_agent
from app.extract import RawRow, parse_section_text


def test_validate_agent_flags_order_and_limits():
    rows = [
        RawRow(
            month="Mar-23",
            area="Bad",
            reference_document="Executed BMRs",
            temp_min=26.0,
            temp_max=24.0,
            rh_min=10.0,
            rh_max=70.0,
            dp_min=1.0,
            dp_max=2.0,
            page=1,
        )
    ]
    r = run_validate_agent(rows)
    assert r.rows_checked == 1
    assert r.rows_invalid == 1
    assert r.rows_valid == 0
    tags = r.issues[0].issues
    assert "temperature_min_gt_max" in tags
    assert "rh_max_exceeds_NMT_60pct" in tags
    assert "differential_pressure_min_below_NLT_1_5_mm_WC" in tags


def test_analyze_agent_monthly_mean_median_mode():
    text = """
6.1 Review of Temperature
Mar-23 Area A Executed BMRs 19 21 30 40 2 3
Mar-23 Area B Executed BMRs 20 22 30 40 2 4
Apr-23 Area A Executed BMRs 18 19 29 39 2 2
"""
    rows = parse_section_text(text)
    a = run_analyze_agent(rows, "Executed BMRs")
    assert len(a.monthly) == 2
    mar = next(m for m in a.monthly if m.month == "Mar-23")
    assert mar.sample_count == 2
    # Mid temps: 20.0 and 21.0 -> mean 20.5, median 20.5, mode [20.0, 21.0] or single if rounded equal
    assert mar.mean_of_midpoint_temp_c == 20.5
    assert mar.median_of_midpoint_temp_c == 20.5
