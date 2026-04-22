"""PDF report generation using WeasyPrint."""
import html
from datetime import datetime


def _severity_color(severity: str) -> str:
    return {"high": "#dc2626", "medium": "#d97706", "low": "#6b7280"}.get(severity, "#6b7280")


def _trend_arrow(trend: str) -> str:
    return {"worsening": "↓", "improving": "↑", "stable": "→"}.get(trend, "→")


def _progress_bar(pct: int, color: str = "#6366f1") -> str:
    safe_pct = max(0, min(100, int(pct)))
    return (
        f'<div class="progress-bar-wrap">'
        f'<div class="progress-bar-fill" style="width:{safe_pct}%; background:{color};"></div>'
        f"</div>"
    )


def _complaint_card(i: int, c: dict) -> str:
    severity = c.get("severity", "low")
    color = _severity_color(severity)
    trend = c.get("trend", "stable")
    pct = c.get("percentage", 0)
    quotes = c.get("example_quotes", [])
    quotes_html = " &nbsp;|&nbsp; ".join(f'&ldquo;{q}&rdquo;' for q in quotes[:3])
    root = f'<p class="root-cause"><strong>Root cause:</strong> {c["root_cause"]}</p>' if c.get("root_cause") else ""
    rec = f'<p class="recommendation">→ {c["recommendation"]}</p>' if c.get("recommendation") else ""
    impact = f'<p class="impact">📈 {c["impact"]}</p>' if c.get("impact") else ""
    q_html = f'<p class="quotes"><em>{quotes_html}</em></p>' if quotes_html else ""
    return (
        f'<div class="section-card complaint-card">'
        f'  <div class="card-header">'
        f'    <span class="card-rank">#{i}</span>'
        f'    <span class="card-title">{c.get("category", "")}</span>'
        f'    <span class="card-pct">{pct}%</span>'
        f"  </div>"
        f"  {_progress_bar(pct, color)}"
        f'  <div class="badges">'
        f'    <span class="badge" style="background:{color}20; color:{color}; border:1px solid {color}40;">'
        f"      {severity.upper()}"
        f"    </span>"
        f'    <span class="badge badge-trend">{_trend_arrow(trend)} {trend.capitalize()}</span>'
        f"  </div>"
        f"  {root}{rec}{impact}{q_html}"
        f"</div>"
    )


def _praise_card(i: int, p: dict) -> str:
    pct = p.get("percentage", 0)
    quotes = p.get("example_quotes", [])
    quotes_html = " &nbsp;|&nbsp; ".join(f'&ldquo;{q}&rdquo;' for q in quotes[:3])
    rec = f'<p class="recommendation">→ {p["recommendation"]}</p>' if p.get("recommendation") else ""
    q_html = f'<p class="quotes"><em>{quotes_html}</em></p>' if quotes_html else ""
    return (
        f'<div class="section-card praise-card">'
        f'  <div class="card-header">'
        f'    <span class="card-rank">#{i}</span>'
        f'    <span class="card-title">{p.get("category", "")}</span>'
        f'    <span class="card-pct">{pct}%</span>'
        f"  </div>"
        f"  {_progress_bar(pct, '#16a34a')}"
        f"  {rec}{q_html}"
        f"</div>"
    )


def _action_card(a: dict) -> str:
    effort = a.get("effort", "medium").capitalize()
    impact = a.get("expected_impact", "medium").capitalize()
    timeframe = a.get("timeframe", "")
    return (
        f'<div class="action-card">'
        f'  <div class="action-priority">PRIORITY {a.get("priority", "")}</div>'
        f'  <p class="action-text">✦ {a.get("action", "")}</p>'
        f'  <div class="action-meta">'
        f"    <span>Effort: <strong>{effort}</strong></span>"
        f"    <span>|</span>"
        f"    <span>Impact: <strong>{impact}</strong></span>"
        f"    <span>|</span>"
        f"    <span>Timeframe: <strong>{timeframe}</strong></span>"
        f"  </div>"
        f"</div>"
    )


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: var(--footer);
        font-size: 9pt;
        color: #64748b;
        border-top: 1px solid #e2e8f0;
        padding-top: 5pt;
    }
}

body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    color: #1e293b;
    line-height: 1.5;
    font-size: 11pt;
}

/* ── Cover ── */
.cover {
    page-break-after: always;
    background: #1a1a2e;
    min-height: 270mm;
    padding: 3cm 2cm;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    margin: -2cm;
}
.cover-logo { font-size: 11pt; color: #6366f1; font-weight: 700; margin-bottom: 2.5cm; letter-spacing: 0.08em; text-transform: uppercase; }
.cover-title { font-size: 26pt; color: #ffffff; font-weight: 800; line-height: 1.2; margin-bottom: 0.8cm; }
.cover-divider { width: 50px; height: 4px; background: #6366f1; margin: 0.8cm auto; border-radius: 2px; }
.cover-subtitle { font-size: 14pt; color: #a5b4fc; font-weight: 500; margin-bottom: 2cm; }
.cover-meta { color: #64748b; font-size: 10pt; line-height: 2.2; }
.cover-meta strong { color: #94a3b8; }

/* ── Sections ── */
.section { page-break-before: always; }
.section-title {
    font-size: 16pt; font-weight: 700; color: #1e293b;
    border-bottom: 2px solid #6366f1; padding-bottom: 7pt; margin-bottom: 18pt;
}
.section-subtitle { font-size: 10pt; color: #64748b; margin-top: -13pt; margin-bottom: 18pt; }

/* ── KPI boxes ── */
.kpi-row { display: flex; gap: 10pt; margin-bottom: 18pt; }
.kpi-box {
    flex: 1; background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 8pt; padding: 12pt 8pt; text-align: center;
}
.kpi-value { font-size: 20pt; font-weight: 800; color: #1e293b; }
.kpi-label { font-size: 7.5pt; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4pt; }

/* ── Summary ── */
.summary-text {
    background: #f8fafc; border-left: 3px solid #6366f1;
    padding: 11pt 14pt; border-radius: 0 6pt 6pt 0;
    margin-bottom: 14pt; font-size: 11pt; color: #374151; line-height: 1.65;
}

/* ── Alerts ── */
.alert-box {
    background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #dc2626;
    border-radius: 6pt; padding: 10pt 14pt; margin-bottom: 14pt;
}
.alert-title { font-weight: 700; color: #dc2626; font-size: 10pt; margin-bottom: 7pt; }
.alert-item { font-size: 10pt; color: #7f1d1d; margin-bottom: 3pt; }

/* ── Cards ── */
.section-card {
    border: 1px solid #e2e8f0; border-radius: 8pt;
    padding: 12pt 14pt; margin-bottom: 10pt;
    page-break-inside: avoid;
}
.complaint-card { border-left: 3px solid #dc2626; }
.praise-card { border-left: 3px solid #16a34a; }
.card-header { display: flex; align-items: baseline; gap: 8pt; margin-bottom: 7pt; }
.card-rank { font-size: 10pt; font-weight: 700; color: #6366f1; }
.card-title { font-size: 12pt; font-weight: 700; color: #1e293b; flex: 1; }
.card-pct { font-size: 13pt; font-weight: 800; color: #1e293b; }
.progress-bar-wrap { height: 6pt; background: #e2e8f0; border-radius: 3pt; margin-bottom: 9pt; overflow: hidden; }
.progress-bar-fill { height: 100%; border-radius: 3pt; }
.badges { display: flex; gap: 8pt; margin-bottom: 7pt; flex-wrap: wrap; }
.badge { font-size: 7.5pt; font-weight: 600; padding: 2pt 7pt; border-radius: 999pt; }
.badge-trend { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }
.root-cause { font-size: 10pt; color: #374151; margin: 5pt 0 3pt; }
.recommendation { font-size: 10pt; color: #4f46e5; margin: 3pt 0; font-weight: 500; }
.impact { font-size: 10pt; color: #16a34a; margin: 3pt 0; }
.quotes { font-size: 9pt; color: #64748b; margin: 5pt 0 0; font-style: italic; }

/* ── Action plan ── */
.action-card {
    border: 1px solid #e2e8f0; border-radius: 8pt;
    padding: 12pt 14pt; margin-bottom: 9pt;
    background: #fafafa; page-break-inside: avoid;
}
.action-priority {
    font-size: 7.5pt; font-weight: 700; color: #6366f1;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 5pt;
}
.action-text { font-size: 12pt; font-weight: 600; color: #1e293b; margin-bottom: 7pt; }
.action-meta { font-size: 9pt; color: #64748b; display: flex; gap: 10pt; flex-wrap: wrap; }

/* ── Opportunities ── */
.opportunity-card {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 6pt; padding: 9pt 12pt; margin-bottom: 7pt;
    font-size: 10pt; color: #1e40af; page-break-inside: avoid;
}

/* ── Comparison ── */
.comparison-box {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8pt;
    padding: 12pt 14pt; margin-bottom: 14pt;
}
.comparison-item { display: flex; gap: 8pt; margin-bottom: 5pt; font-size: 10pt; color: #374151; }
.comparison-label { font-weight: 600; color: #1e293b; min-width: 110pt; }
"""


def generate_pdf_bytes(analysis: dict, meta: dict) -> bytes:
    """
    Generate a PDF Business Intelligence Report from the analysis dict.

    meta = {
        "business_name": str,
        "location_name": str,
        "period_label": str,
        "total_reviews": int,
        "response_rate": int,
        "generated_at": str,  # "April 14, 2026"
    }
    Returns raw PDF bytes.
    """
    business_name = html.escape(meta.get("business_name", "Your Business") or "Your Business")
    location_name = html.escape(meta.get("location_name", "") or "All Locations")
    period_label = html.escape(meta.get("period_label", "") or "")
    total_reviews = meta.get("total_reviews", 0)
    response_rate = meta.get("response_rate", 0)
    generated_at = html.escape(meta.get("generated_at", datetime.now().strftime("%B %d, %Y")) or "")

    avg_rating = float(analysis.get("avg_rating") or 0)
    nps = int(analysis.get("nps_estimate") or 0)
    summary = html.escape(analysis.get("summary", "") or "")
    complaints = analysis.get("complaints", [])
    praises = analysis.get("praises", [])
    urgent_alerts = analysis.get("urgent_alerts", [])
    opportunities = analysis.get("opportunities", [])
    action_plan = analysis.get("action_plan", [])
    comparison = analysis.get("comparison", {})

    # Strip chars that would break the CSS string literal (already html-escaped values are safe for HTML but not for CSS)
    _css_safe = lambda s: s.replace('"', '\u2019').replace('\\', '').replace(';', ',')
    footer_text = f"{_css_safe(meta.get('business_name', 'Your Business') or 'Your Business')} · {_css_safe(meta.get('period_label', '') or '')} · Confidential · Generated by AI Review Responder"
    nps_display = f"+{nps}" if nps >= 0 else str(nps)

    # ── Cover ──────────────────────────────────────────────────────────────
    cover_html = f"""
    <div class="cover">
        <div class="cover-logo">AI Review Responder</div>
        <div class="cover-title">{business_name}</div>
        <div class="cover-divider"></div>
        <div class="cover-subtitle">Customer Review Intelligence Report</div>
        <div class="cover-meta">
            <strong>Period:</strong> {period_label}<br>
            <strong>Location:</strong> {location_name}<br>
            <strong>Generated:</strong> {generated_at}
        </div>
    </div>"""

    # ── Urgent alerts ──────────────────────────────────────────────────────
    alerts_html = ""
    if urgent_alerts:
        items = "".join(f'<div class="alert-item">⚠ {a}</div>' for a in urgent_alerts)
        alerts_html = f"""
        <div class="alert-box">
            <div class="alert-title">🚨 URGENT ALERTS</div>
            {items}
        </div>"""

    # ── Comparison ────────────────────────────────────────────────────────
    comp_html = ""
    if comparison:
        rows = ""
        if comparison.get("vs_previous_period"):
            rows += (
                f'<div class="comparison-item">'
                f'<span class="comparison-label">vs. Previous Period:</span> {comparison["vs_previous_period"]}'
                f"</div>"
            )
        if comparison.get("response_rate"):
            rows += (
                f'<div class="comparison-item">'
                f'<span class="comparison-label">Response Rate:</span> {comparison["response_rate"]}'
                f"</div>"
            )
        if rows:
            comp_html = f'<div class="comparison-box">{rows}</div>'

    # ── Executive summary ─────────────────────────────────────────────────
    exec_html = f"""
    <div class="section">
        <h1 class="section-title">Executive Summary</h1>
        <div class="kpi-row">
            <div class="kpi-box">
                <div class="kpi-value">{total_reviews}</div>
                <div class="kpi-label">Reviews</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-value">{avg_rating:.1f}★</div>
                <div class="kpi-label">Avg Rating</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-value">{response_rate}%</div>
                <div class="kpi-label">Response Rate</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-value">{nps_display}</div>
                <div class="kpi-label">NPS Estimate</div>
            </div>
        </div>
        <div class="summary-text">{summary}</div>
        {alerts_html}
        {comp_html}
    </div>"""

    # ── Complaints ────────────────────────────────────────────────────────
    complaints_html = ""
    if complaints:
        cards = "".join(_complaint_card(i + 1, c) for i, c in enumerate(complaints))
        complaints_html = f"""
        <div class="section">
            <h1 class="section-title">What Customers Complain About</h1>
            <p class="section-subtitle">Areas requiring your attention</p>
            {cards}
        </div>"""

    # ── Praises ───────────────────────────────────────────────────────────
    praises_html = ""
    if praises:
        cards = "".join(_praise_card(i + 1, p) for i, p in enumerate(praises))
        praises_html = f"""
        <div class="section">
            <h1 class="section-title">What Customers Love</h1>
            <p class="section-subtitle">Your strengths — leverage these in marketing</p>
            {cards}
        </div>"""

    # ── Action plan + opportunities ───────────────────────────────────────
    action_html = ""
    if action_plan or opportunities:
        actions = "".join(_action_card(a) for a in action_plan)
        opps_html = ""
        if opportunities:
            items = "".join(f'<div class="opportunity-card">💡 {o}</div>' for o in opportunities)
            opps_html = (
                f"<h2 style='font-size:13pt; font-weight:700; margin:18pt 0 10pt; color:#1e293b;'>"
                f"Opportunities</h2>{items}"
            )
        action_html = f"""
        <div class="section">
            <h1 class="section-title">Action Plan</h1>
            {actions}
            {opps_html}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
{_CSS}
:root {{ --footer: "{footer_text}"; }}
</style>
</head>
<body>
{cover_html}
{exec_html}
{complaints_html}
{praises_html}
{action_html}
</body>
</html>"""

    from weasyprint import HTML  # lazy import — avoids failure when weasyprint is absent at module load
    return HTML(string=html).write_pdf()
