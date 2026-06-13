"""Gates for the downloadable report (CSV + PDF). Deterministic: built from a
small offline battery (no personas, no API). The persona columns are exercised
live during precompute."""

from gauntlet import report
from gauntlet.battery import run_battery
from gauntlet.generator import generate_battery


def _small_battery():
    cases = generate_battery("discrimination", k=4, pop=24, gens=1, seed=0)
    return run_battery(cases, mc_n=2)


def test_csv_has_one_row_per_case_and_worker_columns():
    payload = _small_battery()
    csv_text = report.battery_csv(payload)
    lines = csv_text.strip().split("\n")
    header = lines[0]
    assert lines and len(lines) - 1 == payload["k"]            # one row per case
    for col in ("case_name", "category", "stake_eur", "fitness"):
        assert col in header
    for wid in ("noop", "rules", "llm"):
        assert f"{wid}_score" in header and f"{wid}_pass" in header


def test_category_means_cover_present_categories():
    payload = _small_battery()
    cats, means = report._category_means(payload)
    assert cats and all(c in ("FAULT", "WEATHER", "ECLIPSE", "COMBO") for c in cats)
    for wid, *_ in report._workers(payload):
        assert len(means[wid]) == len(cats)


def test_pdf_is_a_valid_document_with_charts():
    payload = _small_battery()
    pdf = report.battery_pdf(payload, "discrimination")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 5000   # contains the embedded chart PNGs, not just text
