"""PDF test report generation."""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

STATUS_COLORS = {
    "passed": colors.HexColor("#16a34a"),
    "healed": colors.HexColor("#2563eb"),
    "failed": colors.HexColor("#dc2626"),
    "error": colors.HexColor("#ea580c"),
}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_pdf(project: dict, run: dict, tests_by_id: dict[int, dict], artifacts_dir: Path) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="WebSentinel-AI Report",
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=10)
    story = [
        Paragraph("WebSentinel-AI — Test Report", styles["Title"]),
        Paragraph(f"<b>Project:</b> {esc(project['name'])} &nbsp; <b>URL:</b> {esc(project['base_url'])}", styles["BodyText"]),
        Paragraph(
            f"<b>Run #{run['id']}</b> &nbsp; started {run['started_at']} &nbsp; finished {run.get('finished_at') or '-'}",
            styles["BodyText"],
        ),
        Spacer(1, 6 * mm),
    ]
    s = run.get("summary") or {}
    summary = Table(
        [
            ["Total", "Passed", "Healed", "Failed", "Errors", "Pass rate", "Duration"],
            [
                s.get("total", 0),
                s.get("passed", 0),
                s.get("healed", 0),
                s.get("failed", 0),
                s.get("error", 0),
                f"{s.get('pass_rate', 0)}%",
                f"{s.get('duration_ms', 0) / 1000:.1f}s",
            ],
        ],
        hAlign="LEFT",
    )
    summary.setStyle(table_style())
    story += [summary, Spacer(1, 6 * mm)]

    root_causes = s.get("root_causes", [])
    story.append(Paragraph(f"Root cause analysis ({len(root_causes)} likely causes)", styles["Heading2"]))
    if root_causes:
        for finding in root_causes:
            story.append(Paragraph(
                f"<b>[{esc(finding.get('severity', 'medium').upper())}] {esc(finding.get('title', 'Likely cause'))}</b> "
                f"— confidence {round(float(finding.get('confidence', 0)) * 100)}%",
                styles["BodyText"],
            ))
            story.append(Paragraph(f"Affected tests: {esc(', '.join(finding.get('affected_tests', [])))}", small))
            for evidence in finding.get("evidence", []):
                story.append(Paragraph(f"Evidence: {esc(evidence)}", small))
            story.append(Paragraph(f"Suggested fix: {esc(finding.get('suggested_fix', 'Review the failure evidence.'))}", small))
            story.append(Paragraph(f"Analysis method: {esc(finding.get('method', ''))}. This is a likely cause, not a confirmed diagnosis.", small))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("No failure pattern was confidently classified. Review individual failure evidence below.", small))
    story.append(Spacer(1, 4 * mm))

    results = run.get("results", [])
    raw_bugs = [r for r in results if r["status"] in ("failed", "error")]
    grouped = (s.get("bugs") or [])
    if not grouped:
        grouped = [{"title": r["title"], "error": r.get("error", ""), "occurrences": 1,
                    "result_indices": [i]} for i, r in enumerate(results) if r["status"] in ("failed", "error")]
    grouped.sort(key=lambda g: SEVERITY_ORDER.get(
        tests_by_id.get(results[g["result_indices"][0]].get("test_id"), {}).get("severity", "low"), 9
    ) if g.get("result_indices") else 9)
    story.append(Paragraph(
        f"Unique bugs found ({len(grouped)}) — {len(raw_bugs)} failing test results", styles["Heading2"]
    ))
    if not grouped:
        story.append(Paragraph("No bugs found. All tests passed.", styles["BodyText"]))
    for group in grouped:
        first_index = group.get("result_indices", [0])[0]
        r = results[first_index] if results else {}
        test = tests_by_id.get(r.get("test_id"), {})
        story.append(Paragraph(
            f"<b>[{test.get('severity', '?').upper()}] {esc(group.get('title', r.get('title', 'Failure')))}</b> "
            f"— {group.get('occurrences', 1)} occurrence(s)", styles["BodyText"]
        ))
        story.append(Paragraph(esc(test.get("description", "")), small))
        story.append(Paragraph(f"<font color='#dc2626'>{esc(group.get('error', r.get('error', '')))}</font>", small))
        shot_name = (group.get("screenshots") or [r.get("screenshot")])[0]
        shot = artifacts_dir / shot_name if shot_name else None
        if shot and shot.exists():
            story.append(Image(str(shot), width=120 * mm, height=75 * mm))
        story.append(Spacer(1, 4 * mm))

    healed = [(r, h) for r in results for h in r.get("healed", [])]
    if healed:
        story.append(Paragraph(f"Self-healed locators ({len(healed)})", styles["Heading2"]))
        rows = [["Test", "Element", "Old selector", "New selector", "Score"]]
        rows += [
            [
                Paragraph(esc(r["title"]), small),
                Paragraph(esc(h["element"]), small),
                Paragraph(esc(h["old_css"]), small),
                Paragraph(esc(h["new_css"]), small),
                f"{h['score']:.2f}",
            ]
            for r, h in healed
        ]
        t = Table(rows, colWidths=[50 * mm, 35 * mm, 35 * mm, 35 * mm, 15 * mm], hAlign="LEFT")
        t.setStyle(table_style())
        story += [t, Spacer(1, 4 * mm)]

    story.append(Paragraph("All test results", styles["Heading2"]))
    rows = [["#", "Test", "Category", "Severity", "Status", "Time"]]
    for i, r in enumerate(results, 1):
        test = tests_by_id.get(r["test_id"], {})
        rows.append(
            [
                i,
                Paragraph(esc(r["title"]), small),
                test.get("category", ""),
                test.get("severity", ""),
                r["status"].upper(),
                f"{r['duration_ms'] / 1000:.1f}s",
            ]
        )
    t = Table(rows, colWidths=[8 * mm, 85 * mm, 22 * mm, 20 * mm, 18 * mm, 15 * mm], hAlign="LEFT", repeatRows=1)
    style = table_style()
    for i, r in enumerate(results, 1):
        style.add("TEXTCOLOR", (4, i), (4, i), STATUS_COLORS.get(r["status"], colors.black))
    t.setStyle(style)
    story.append(t)
    doc.build(story)
    return buf.getvalue()


def table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ]
    )


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
