"""Downloadable battery reports: a CSV of the cases plus results, and a typeset
PDF (certification table, the two comparison charts, a case appendix).

The charts are drawn server-side with matplotlib (Agg, headless) and embedded
into a reportlab document. Both deps are pip-only with no system libraries.
"""

import csv
import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # headless: no display needed
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,  # noqa: E402
                                Table, TableStyle)

CATEGORY_ORDER = ["FAULT", "WEATHER", "ECLIPSE", "COMBO"]
WORKER_COLOR = {
    "noop": "#8b949e", "rules": "#f85149", "llm": "#3fb950",
    "ds-cautious": "#58a6ff", "ds-balanced": "#a371f7", "ds-aggressive": "#d29922",
}
SHORT = {"noop": "None", "rules": "Rules", "llm": "Mock",
         "ds-cautious": "Cau", "ds-balanced": "Bal", "ds-aggressive": "Agg"}


def _workers(payload: dict) -> list:
    """Ordered [(id, label, kind, report_row)] for every worker in the battery."""
    return [(w["id"], w["label"], w["kind"], payload["report"][w["id"]])
            for w in payload["workers"] if w["id"] in payload["report"]]


def _color(wid: str) -> str:
    return WORKER_COLOR.get(wid, "#888888")


# ---------------- CSV ----------------

def battery_csv(payload: dict) -> str:
    workers = _workers(payload)
    buf = io.StringIO()
    w = csv.writer(buf)
    head = ["case_name", "category", "label", "stake_eur", "floor_eur", "oracle_eur", "fitness"]
    for wid, _, _, _ in workers:
        head += [f"{wid}_score", f"{wid}_pass"]
    w.writerow(head)
    for c in payload["cases"]:
        row = [c["name"], c["category"], c["label"],
               round(c["stake"]), round(c["floor"]), round(c["oracle"]), c["fitness"]]
        for wid, _, _, _ in workers:
            a = c["agents"][wid]
            row += [round(a["mean"], 4), int(a["mean"] >= 0.5)]
        w.writerow(row)
    return buf.getvalue()


# ---------------- charts ----------------

def _category_means(payload: dict) -> tuple:
    """(categories_present, {worker_id: [mean per category]})."""
    cats = [c for c in CATEGORY_ORDER if any(x["category"] == c for x in payload["cases"])]
    means = {}
    for wid, _, _, _ in _workers(payload):
        row = []
        for cat in cats:
            vals = [c["agents"][wid]["mean"] for c in payload["cases"] if c["category"] == cat]
            row.append(float(np.mean(vals)) if vals else 0.0)
        means[wid] = row
    return cats, means


def grouped_bar_png(payload: dict) -> bytes:
    cats, means = _category_means(payload)
    workers = _workers(payload)
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=150)
    x = np.arange(len(cats))
    n = len(workers)
    width = 0.8 / max(n, 1)
    for i, (wid, label, _, _) in enumerate(workers):
        ax.bar(x + (i - (n - 1) / 2) * width, [v * 100 for v in means[wid]], width,
               label=label, color=_color(wid))
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.set_ylabel("mean recovered (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Recovery by failure mode")
    ax.legend(fontsize=6, ncol=3, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_bytes(fig)


def scatter_png(payload: dict) -> bytes:
    workers = _workers(payload)
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=150)
    for wid, label, _, r in workers:
        ax.scatter(r["pass_rate"] * 100, r["p10"] * 100, s=90, color=_color(wid),
                   edgecolors="white", linewidths=0.6, zorder=3)
        ax.annotate(label, (r["pass_rate"] * 100, r["p10"] * 100),
                    textcoords="offset points", xytext=(6, 4), fontsize=7)
    ax.set_xlabel("pass-rate, reward (%)")
    ax.set_ylabel("worst-case P10, tail safety (%)")
    ax.set_title("Risk vs return")
    ax.grid(alpha=0.3)
    ax.set_xlim(-3, 103)
    ax.set_ylim(-3, max(40, *(r["p10"] * 100 for *_, r in workers)) + 8)
    fig.tight_layout()
    return _fig_bytes(fig)


def _fig_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ---------------- PDF ----------------

def battery_pdf(payload: dict, mode: str) -> bytes:
    workers = _workers(payload)
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.4 * cm, bottomMargin=1.2 * cm,
                            leftMargin=1.4 * cm, rightMargin=1.4 * cm,
                            title=f"Gauntlet certification report ({mode})")
    elems = []

    elems.append(Paragraph("Gauntlet Certification Report", styles["Title"]))
    sub = (f"Battery: <b>{mode}</b> &nbsp;|&nbsp; {payload['k']} generated test days "
           f"&nbsp;|&nbsp; seed {payload.get('seed', 0)} &nbsp;|&nbsp; "
           f"generated {datetime.now():%Y-%m-%d %H:%M}")
    elems.append(Paragraph(sub, styles["Normal"]))
    elems.append(Spacer(1, 0.3 * cm))

    method = ("Each day is a generated stress scenario chosen for recoverable money at stake "
              "(do-nothing cost minus a perfect-foresight oracle) and for separating competent "
              "agents from naive ones. Every worker is scored as the share of the recoverable loss "
              "it recovers, bracketed between the oracle (100%) and doing nothing (0%). Deterministic "
              "workers are averaged over Monte-Carlo jitter per day; DeepSeek personas are a single "
              "run per day (API-bound) and labelled as such. Pass-rate is the share of days scoring "
              "at least 50%; worst-case P10 is the tenth-percentile day, the tail behind the average.")
    elems.append(Paragraph(method, styles["BodyText"]))
    elems.append(Spacer(1, 0.3 * cm))

    # certification table
    elems.append(Paragraph("<b>Certification report</b>", styles["Heading2"]))
    head = ["Worker", "Kind", "Pass-rate", "Worst P10", "Mean", "Hardest day (score)"]
    rows = [head]
    for wid, label, kind, r in workers:
        rows.append([
            label, kind, f"{r['pass_rate']*100:.0f}%", f"{r['p10']*100:.0f}%",
            f"{r['mean']*100:.0f}%",
            Paragraph(f"{r['hardest']['label']} <b>({r['hardest']['mean']*100:.0f}%)</b>",
                      styles["BodyText"]),
        ])
    t = Table(rows, colWidths=[2.6 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.4 * cm, 6.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#21262d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 0.4 * cm))

    # charts
    elems.append(Paragraph("<b>Worker comparison</b>", styles["Heading2"]))
    for png in (grouped_bar_png(payload), scatter_png(payload)):
        elems.append(Image(io.BytesIO(png), width=16 * cm, height=7.5 * cm))
        elems.append(Spacer(1, 0.2 * cm))

    # case appendix
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(Paragraph("<b>Generated cases (hardest first)</b>", styles["Heading2"]))
    legend = " &nbsp; ".join(f"{SHORT[wid]}={label}" for wid, label, _, _ in workers if wid in SHORT)
    elems.append(Paragraph(f"<font size=7>{legend}; values are mean recovered %.</font>", styles["BodyText"]))
    ahead = ["Case", "Cat", "Stake EUR"] + [SHORT.get(wid, wid[:4]) for wid, *_ in workers]
    arows = [ahead]
    for c in payload["cases"]:
        arows.append([c["name"], c["category"], f"{round(c['stake']):,}"]
                     + [f"{c['agents'][wid]['mean']*100:.0f}" for wid, *_ in workers])
    at = Table(arows, repeatRows=1)
    at.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#21262d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    elems.append(at)

    doc.build(elems)
    return buf.getvalue()
