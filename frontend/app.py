import importlib
import json
import sys
import time
from pathlib import Path

import fitz
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
MODULES_DIR = APP_DIR / "modules"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))

st.set_page_config(
    page_title="DPR Review Studio",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --ink: #10233f;
        --muted: #5b6577;
        --surface: rgba(255, 255, 255, 0.86);
        --line: rgba(16, 35, 63, 0.10);
        --shadow: 0 18px 60px rgba(16, 35, 63, 0.10);
        --accent: #0f766e;
        --accent-2: #c27803;
        --danger: #b42318;
        --success: #15803d;
        --warning: #b45309;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 26%),
            radial-gradient(circle at top right, rgba(194, 120, 3, 0.16), transparent 24%),
            linear-gradient(180deg, #f6f8fb 0%, #eef3f7 100%);
        color: var(--ink);
        font-family: 'Inter', sans-serif;
    }

    .hero {
        padding: 2rem 2rem 1.5rem 2rem;
        border: 1px solid var(--line);
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(245,248,251,0.82));
        box-shadow: var(--shadow);
        margin-bottom: 1rem;
    }

    .eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.76rem;
        font-weight: 700;
        color: var(--accent);
        margin-bottom: 0.4rem;
    }

    .hero h1 {
        font-family: 'Fraunces', serif;
        font-size: clamp(2.1rem, 3vw, 3.6rem);
        margin: 0;
        color: var(--ink);
    }

    .hero p {
        max-width: 920px;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.7;
        margin-top: 0.75rem;
    }

    .panel {
        border: 1px solid var(--line);
        border-radius: 24px;
        background: var(--surface);
        box-shadow: var(--shadow);
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        border: 1px solid var(--line);
        border-radius: 20px;
        background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(245,249,252,0.88));
        box-shadow: 0 10px 34px rgba(16, 35, 63, 0.08);
        padding: 1rem 1.05rem;
        min-height: 118px;
    }

    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.10em;
        color: var(--muted);
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-size: 2rem;
        line-height: 1;
        font-weight: 800;
        color: var(--ink);
        margin-bottom: 0.35rem;
    }

    .metric-note {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.5;
    }

    .ring-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 240px;
    }

    .ring {
        width: 210px;
        height: 210px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: radial-gradient(circle at center, rgba(255,255,255,0.95) 0 58%, transparent 59%),
            conic-gradient(var(--accent) 0 var(--pct), rgba(16,35,63,0.12) var(--pct) 100%);
        box-shadow: 0 18px 50px rgba(16, 35, 63, 0.14);
        border: 1px solid var(--line);
    }

    .ring-inner {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,249,252,0.92));
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 1rem;
    }

    .ring-score {
        font-family: 'Fraunces', serif;
        font-size: 2.8rem;
        line-height: 1;
        color: var(--ink);
    }

    .ring-label {
        margin-top: 0.35rem;
        color: var(--muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 700;
    }

    .workflow {
        display: grid;
        gap: 0.65rem;
    }

    .workflow-step {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.7rem 0.85rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--line);
    }

    .workflow-step.done {
        background: rgba(21,128,61,0.08);
        border-color: rgba(21,128,61,0.20);
    }

    .workflow-pill {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        font-weight: 800;
        font-size: 0.8rem;
        background: rgba(16,35,63,0.08);
        color: var(--ink);
        flex: 0 0 auto;
    }

    .workflow-step.done .workflow-pill {
        background: rgba(21,128,61,0.16);
        color: var(--success);
    }

    .workflow-text {
        font-weight: 600;
        color: var(--ink);
    }

    .workflow-subtext {
        color: var(--muted);
        font-size: 0.88rem;
        margin-left: auto;
    }

    .recommendation-box {
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255,255,255,0.86);
        padding: 0.9rem 1rem;
        margin-bottom: 0.75rem;
    }

    .section-summary-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.7rem;
        margin-top: 0.85rem;
        margin-bottom: 0.8rem;
    }

    .section-mini {
        padding: 0.8rem 0.9rem;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: rgba(255,255,255,0.9);
    }

    .section-mini .name {
        font-weight: 800;
        color: var(--ink);
    }

    .section-mini .value {
        font-family: 'Fraunces', serif;
        font-size: 1.7rem;
        color: var(--ink);
        margin-top: 0.2rem;
    }

    .section-card {
        border: 1px solid var(--line);
        border-radius: 22px;
        background: rgba(255,255,255,0.88);
        box-shadow: 0 12px 38px rgba(16,35,63,0.08);
        padding: 1rem 1rem 0.85rem 1rem;
        margin-bottom: 1rem;
    }

    .badge {
        display: inline-block;
        padding: 0.32rem 0.7rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-right: 0.4rem;
        margin-bottom: 0.35rem;
        border: 1px solid var(--line);
    }

    .badge-accent { background: rgba(15,118,110,0.10); color: var(--accent); }
    .badge-warn { background: rgba(180,83,9,0.10); color: var(--warning); }
    .badge-danger { background: rgba(180,35,24,0.10); color: var(--danger); }
    .badge-success { background: rgba(21,128,61,0.10); color: var(--success); }

    .subtle {
        color: var(--muted);
        font-size: 0.92rem;
    }

    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(16,35,63,0.16), transparent);
        margin: 1rem 0;
    }

    div[data-testid="stMetric"] {
        background: transparent;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.85rem 1rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.75);
        border: 1px solid var(--line);
        font-weight: 700;
    }

    @keyframes pulseGlow {
        0%, 100% { transform: scale(1); opacity: 0.72; }
        50% { transform: scale(1.08); opacity: 1; }
    }

    @keyframes slideUp {
        from { transform: translateY(12px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    .loading-shell {
        border: 1px solid var(--line);
        border-radius: 24px;
        background: rgba(255,255,255,0.9);
        box-shadow: var(--shadow);
        padding: 0.95rem 1rem 0.9rem 1rem;
        margin-bottom: 1rem;
        animation: slideUp 0.4s ease-out;
    }

    .loading-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.8rem;
    }

    .loading-title {
        font-family: 'Fraunces', serif;
        font-size: 1.35rem;
        color: var(--ink);
    }

    .loading-dots {
        display: inline-flex;
        gap: 0.35rem;
        align-items: center;
    }

    .loading-dots span {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--accent);
        display: inline-block;
        animation: pulseGlow 1s infinite ease-in-out;
    }

    .loading-dots span:nth-child(2) { animation-delay: 0.15s; }
    .loading-dots span:nth-child(3) { animation-delay: 0.3s; }

    .current-stage {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.8rem 0.9rem;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255,255,255,0.9);
        box-shadow: 0 12px 28px rgba(16,35,63,0.06);
    }

    .current-stage .dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 0 0 rgba(15,118,110,0.35);
        animation: pulseGlow 1s infinite ease-in-out;
        flex: 0 0 auto;
    }

    .current-stage .label {
        font-weight: 800;
        color: var(--ink);
    }

    .current-stage .detail {
        color: var(--muted);
        font-size: 0.92rem;
    }

    .completed-strip {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 0.75rem;
    }

    .completed-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.38rem 0.7rem;
        border-radius: 999px;
        background: rgba(21,128,61,0.10);
        border: 1px solid rgba(21,128,61,0.18);
        color: var(--success);
        font-weight: 700;
        font-size: 0.8rem;
    }

    .stage-stack {
        display: grid;
        gap: 0.6rem;
    }

    .report-tabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.9);
    }

    .stage-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.9rem;
        padding: 0.7rem 0.85rem;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(255,255,255,0.8);
    }

    .stage-item.active {
        border-color: rgba(15,118,110,0.35);
        background: rgba(15,118,110,0.08);
    }

    .stage-item.done {
        border-color: rgba(21,128,61,0.25);
        background: rgba(21,128,61,0.08);
    }

    .stage-name {
        font-weight: 700;
        color: var(--ink);
    }

    .stage-detail {
        color: var(--muted);
        font-size: 0.88rem;
    }

    .stage-pill {
        min-width: 88px;
        text-align: center;
        border-radius: 999px;
        padding: 0.32rem 0.7rem;
        font-weight: 700;
        font-size: 0.78rem;
        border: 1px solid var(--line);
        color: var(--ink);
        background: rgba(255,255,255,0.88);
    }

    .stage-item.done .stage-pill {
        color: var(--success);
        background: rgba(21,128,61,0.12);
        border-color: rgba(21,128,61,0.18);
    }

    .stage-item.active .stage-pill {
        color: var(--accent);
        background: rgba(15,118,110,0.14);
        border-color: rgba(15,118,110,0.20);
    }

    .jump-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.75rem;
    }

    .jump-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.38rem 0.75rem;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: rgba(255,255,255,0.88);
        color: var(--ink);
        font-weight: 700;
        font-size: 0.8rem;
        text-decoration: none;
    }

    .bottom-right-popup {
        position: fixed;
        right: 1rem;
        bottom: 1rem;
        z-index: 99999;
        width: min(360px, calc(100vw - 2rem));
        border-radius: 18px;
        border: 1px solid rgba(21,128,61,0.22);
        background: rgba(255,255,255,0.96);
        box-shadow: 0 22px 60px rgba(16, 35, 63, 0.18);
        padding: 0.9rem 1rem;
        animation: slideUp 0.5s ease-out;
    }

    .bottom-right-popup .title {
        font-weight: 800;
        color: var(--success);
        margin-bottom: 0.2rem;
    }

    .bottom-right-popup .text {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.4;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


def _default_pdf_path():
    sample = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if sample.exists():
        return sample
    fallback = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    return fallback


def _load_pipeline_module():
    return importlib.import_module("backend.services.pipeline_service")


def _run_full_analysis(pdf_path):
    pipeline_module = _load_pipeline_module()
    return pipeline_module.run_pipeline(pdf_path)


def _risk_badge(level):
    level = str(level or "").strip().lower()
    if level == "high":
        return "badge badge-danger", "High"
    if level == "medium":
        return "badge badge-warn", "Medium"
    return "badge badge-success", "Low"


def _score_badge(score):
    if score >= 80:
        return "badge badge-success"
    if score >= 60:
        return "badge badge-warn"
    return "badge badge-danger"


def _score_icon(score):
    if score >= 80:
        return "🟢"
    if score >= 60:
        return "🟡"
    return "🔴"


def _render_full_json(data, label):
    st.markdown(f"**{label}**")
    st.code(json.dumps(data, indent=2, ensure_ascii=False), language="json")


def _render_score_ring(score, label, sublabel=""):
    score = max(0.0, min(100.0, float(score or 0.0)))
    st.markdown(
        f"""
        <div class="ring-wrap">
            <div class="ring" style="--pct: {score}%;">
                <div class="ring-inner">
                    <div class="ring-score">{score:.0f}</div>
                    <div class="ring-label">{label}</div>
                    <div class="subtle" style="margin-top: 0.35rem;">{sublabel}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _set_focus(section_name):
    st.session_state.focus_section = section_name


def _render_navigation_chips():
    focus = st.session_state.get("focus_section", "overview")
    labels = [
        ("overview", "Overview"),
        ("completeness", "Completeness"),
        ("quality", "Quality"),
        ("features", "Features"),
        ("risk", "Risk"),
    ]
    chips = []
    for key, label in labels:
        active_class = "style='border-color: rgba(15,118,110,0.35); background: rgba(15,118,110,0.10);'" if key == focus else ""
        chips.append(f"<a class='jump-chip' {active_class} href='#{key}'>{label}</a>")
    st.markdown("<div class='jump-row'>" + "".join(chips) + "</div>", unsafe_allow_html=True)


def _render_loading_shell(target, active_step, completed_steps):
    completed_steps = completed_steps or []
    target.markdown(
        f"""
        <div class="loading-shell">
            <div class="loading-head">
                <div>
                    <div class="eyebrow">Processing</div>
                    <div class="loading-title">DPR analysis is running</div>
                </div>
                <div class="loading-dots"><span></span></div>
            </div>
            <div class="current-stage">
                <div class="dot"></div>
                <div>
                    <div class="label">Current process: {active_step}</div>
                    <div class="detail">The finished batches appear below as each step completes.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if completed_steps:
        chips = "".join(f"<span class='completed-chip'>✓ {step}</span>" for step in completed_steps)
        target.markdown(f"<div class='completed-strip'>{chips}</div>", unsafe_allow_html=True)


def _render_completion_popup(report):
    risk = report.get("risk", {}) if isinstance(report, dict) else {}
    score = risk.get("risk_score", 0.0)
    risk_level = risk.get("overall_risk", "Unknown")
    st.markdown(
        f"""
        <div class="bottom-right-popup">
            <div class="title">Report generated</div>
            <div class="text">Overall DPR score: <strong>{score:.0f}/100</strong><br>Overall risk: <strong>{risk_level}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_pdf_report_bytes(report):
    completeness = report.get("completeness", {}).get("summary", {}) if isinstance(report, dict) else {}
    quality = report.get("quality", {}).get("summary", {}) if isinstance(report, dict) else {}
    risk = report.get("risk", {}) if isinstance(report, dict) else {}
    features = report.get("features", {}) if isinstance(report, dict) else {}

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    margin_x = 42
    y = 46

    def write_line(text, size=11, color=(16 / 255, 35 / 255, 63 / 255), gap=16, bold=False):
        nonlocal y, page
        # Use a built-in font only; bundled fonts are not available in this workspace.
        page.insert_text((margin_x, y), text, fontsize=size, fontname="helv", color=color)
        y += gap

    def ensure_space(lines=1):
        nonlocal page, y
        if y > 770:
            page = doc.new_page(width=595, height=842)
            y = 46

    write_line("MDoNER DPR Review Studio", size=18, gap=24)
    write_line(f"Overall DPR Score: {float(risk.get('risk_score', 0.0) or 0.0):.0f}/100", size=15, gap=20)
    write_line(f"Overall Risk: {risk.get('overall_risk', 'Unknown')}", size=12, gap=18)
    write_line(f"Completeness: {float(completeness.get('overall_score', 0.0) or 0.0):.2f}", size=12, gap=18)
    write_line(f"Quality: {float(quality.get('overall_quality', 0.0) or 0.0):.2f}", size=12, gap=18)
    write_line("", gap=6)

    sections = [
        ("Top Issues", risk.get("top_issues", []) or []),
        ("Recommendations", risk.get("recommendations", []) or []),
        ("Missing Sections", features.get("missing_sections", []) or []),
    ]

    for title, items in sections:
        ensure_space()
        write_line(title, size=13, gap=18)
        if not items:
            write_line("- None", size=11, gap=16)
        else:
            for item in items:
                ensure_space()
                write_line(f"- {item}", size=11, gap=15)
        write_line("", gap=6)

    breakdown = risk.get("rule_breakdown", {}) if isinstance(risk, dict) else {}
    if breakdown:
        ensure_space()
        write_line("Risk Breakdown", size=13, gap=18)
        for key, data in breakdown.items():
            ensure_space()
            drivers = "; ".join(data.get("drivers", []))
            write_line(f"{key.replace('_', ' ').title()}: {data.get('score', 0.0)}", size=11, gap=15)
            if drivers:
                write_line(drivers, size=10, color=(0.3, 0.35, 0.42), gap=14)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _render_stage_tabs(report):
    classified = report.get("classified_sections", {}).get("sections", []) if isinstance(report, dict) else []
    completeness = report.get("completeness", {}) if isinstance(report, dict) else {}
    completeness_summary = completeness.get("summary", {}) if isinstance(completeness, dict) else {}
    completeness_sections = completeness.get("sections", []) if isinstance(completeness, dict) else []
    quality = report.get("quality", {}) if isinstance(report, dict) else {}
    quality_summary = quality.get("summary", {}) if isinstance(quality, dict) else {}
    quality_sections = quality.get("sections", []) if isinstance(quality, dict) else []
    features = report.get("features", {}) if isinstance(report, dict) else {}
    risk = report.get("risk", {}) if isinstance(report, dict) else {}

    tabs = st.tabs(["Classified", "Completeness", "Quality", "Features", "Risk"])

    with tabs[0]:
        st.markdown("<div class='panel'><div class='eyebrow'>Done</div><h3 style='margin:0.2rem 0;'>Classified sections are ready</h3><div class='subtle'>The document structure has been identified and normalized.</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='completed-strip'><span class='completed-chip'>✓ {len(classified)} sections found</span></div>", unsafe_allow_html=True)
        for section in classified[:3]:
            st.markdown(f"- **{section.get('title') or section.get('section')}** · {section.get('category', '')}")
        if len(classified) > 3:
            st.caption(f"+ {len(classified) - 3} more sections")
        with st.expander("Show classified JSON", expanded=True):
            _render_full_json(report.get("classified_sections", {}), "Classified JSON")

    with tabs[1]:
        st.markdown("<div class='panel'><div class='eyebrow'>Done</div><h3 style='margin:0.2rem 0;'>Completeness finished</h3><div class='subtle'>This tab shows the section completeness result as a compact batch.</div></div>", unsafe_allow_html=True)
        st.metric("Overall completeness", f"{float(completeness_summary.get('overall_score', 0.0) or 0.0):.2f}")
        st.write("Weakest sections:")
        st.write(", ".join(completeness_summary.get("weakest_sections", [])) or "None")
        st.write("Missing sections:")
        st.write(", ".join(completeness_summary.get("missing_sections", [])) or "None")
        st.markdown("### Full completeness output")
        for index, section in enumerate(completeness_sections, start=1):
            _render_section_card(index, section, mode="completeness")
        with st.expander("Show completeness JSON", expanded=True):
            _render_full_json(completeness, "Completeness JSON")
    with tabs[2]:
        st.markdown("<div class='panel'><div class='eyebrow'>Done</div><h3 style='margin:0.2rem 0;'>Quality finished</h3><div class='subtle'>The quality score is available in a neat, reviewer-friendly view.</div></div>", unsafe_allow_html=True)
        st.metric("Overall quality", f"{float(quality_summary.get('overall_quality', 0.0) or 0.0):.0f}")
        st.write("Strongest sections:")
        st.write(", ".join(quality_summary.get("strongest_sections", [])) or "None")
        st.write("Weakest sections:")
        st.write(", ".join(quality_summary.get("weakest_sections", [])) or "None")
        with st.expander("Show quality JSON", expanded=True):
            _render_full_json(quality, "Quality JSON")

    with tabs[3]:
        st.markdown("<div class='panel'><div class='eyebrow'>Done</div><h3 style='margin:0.2rem 0;'>Feature Builder results</h3><div class='subtle'>These compact metrics feed the risk engine.</div></div>", unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            st.metric("Overall completeness", f"{float(features.get('overall_completeness', 0.0) or 0.0):.2f}")
            st.metric("Section count", int(features.get("section_count", 0) or 0))
        with right:
            st.metric("Overall quality", f"{float(features.get('overall_quality', 0.0) or 0.0):.2f}")
            st.write("Missing sections:")
            st.write(", ".join(features.get("missing_sections", [])) or "None")
        with st.expander("Show features JSON", expanded=True):
            _render_full_json(features, "Features JSON")

    with tabs[4]:
        st.markdown("<div class='panel'><div class='eyebrow'>Done</div><h3 style='margin:0.2rem 0;'>Risk report</h3><div class='subtle'>This is the final generated assessment.</div></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall risk", str(risk.get("overall_risk", "Unknown")))
        c2.metric("Risk score", f"{float(risk.get('risk_score', 0.0) or 0.0):.1f}")
        c3.metric("Confidence", f"{float(risk.get('confidence', 0.0) or 0.0):.1f}")
        st.write("Top issues:")
        st.write("\n".join([f"- {item}" for item in risk.get("top_issues", [])]) or "None")
        st.write("Recommendations:")
        st.write("\n".join([f"- {item}" for item in risk.get("recommendations", [])]) or "None")
        with st.expander("Show risk JSON", expanded=True):
            _render_full_json(risk, "Risk JSON")


def _render_quick_toc():
    st.markdown('<div class="panel"><div class="eyebrow">Quick TOC</div><div class="subtle">Jump fast to the main report sections.</div></div>', unsafe_allow_html=True)
    labels = [
        ("overview", "Overview"),
        ("completeness", "Completeness"),
        ("quality", "Quality"),
        ("features", "Features"),
        ("risk", "Risk"),
    ]
    cols = st.columns(len(labels))
    for col, (key, label) in zip(cols, labels):
        with col:
            pressed = st.button(label, key=f"toc_{key}", use_container_width=True)
            if pressed:
                st.session_state.focus_section = key
    if st.session_state.get("focus_section"):
        st.caption(f"Focused section: {st.session_state.focus_section.title()}")


def _render_live_panel(target, title, subtitle, metrics=None, summary=None, json_data=None, jump_label=None, jump_section=None, accent="accent"):
    metrics = metrics or []
    summary = summary or []
    metric_html = "".join(
        f"<div class='section-mini'><div class='name'>{name}</div><div class='value' style='font-size:1.35rem;'>{value}</div></div>"
        for name, value in metrics
    )
    summary_html = "".join(f"<div class='recommendation-box' style='margin-bottom:0.45rem;'>{item}</div>" for item in summary)

    with target.container():
        st.markdown(
            f"""
            <div class="section-card">
                <div class="badge badge-{accent}">{title}</div>
                <h3 style="margin: 0.35rem 0 0.2rem 0; color: var(--ink);">{subtitle}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if metric_html:
            st.markdown(f"<div class='section-summary-grid'>{metric_html}</div>", unsafe_allow_html=True)
        if summary_html:
            st.markdown(summary_html, unsafe_allow_html=True)
        if jump_label and jump_section:
            st.button(jump_label, key=f"jump_{jump_section}_{title}", on_click=_set_focus, args=(jump_section,))
        if json_data is not None:
            with st.expander(f"Show {title} JSON", expanded=True):
                _render_full_json(json_data, f"{title} JSON")


def _run_live_analysis(pdf_path, loading_slot, progress_slot, completion_slot, panels):
    section_detector_module = importlib.import_module("modules.structure.toc_detector")
    classifier_module = importlib.import_module("modules.classification.section_classifier")
    completeness_module = importlib.import_module("modules.analysis.completeness_checker")
    quality_module = importlib.import_module("modules.analysis.quality_checker")
    feature_module = importlib.import_module("modules.features.feature_builder")
    risk_module = importlib.import_module("modules.risk.risk_engine")

    steps_done = []

    def advance(step_name, progress_value):
        steps_done.append(step_name)
        progress_slot.progress(progress_value)
        loading_slot.empty()
        _render_loading_shell(loading_slot, step_name, steps_done)

    advance("Reading PDF", 0.08)
    section_detector = section_detector_module.SectionDetector()
    json_data = section_detector.pdfreader.get_pdf_data(str(pdf_path))
    time.sleep(0.05)

    advance("Finding TOC", 0.18)
    page_content = section_detector.call_llm_for_structure(json_data)
    toc_json = section_detector.toc_json(page_content)
    time.sleep(0.05)

    advance("Classifying Sections", 0.32)
    document_structure = section_detector.classify_json(toc_json, json_data)
    classifier = classifier_module.SectionClassifier()
    classified_output = classifier.classify_sections(document_structure)
    _render_live_panel(
        panels["classified"],
        "Stage 1",
        "Classified Sections",
        metrics=[("Sections Found", len(classified_output.get("sections", []))), ("Source", "Document structure")],
        summary=["The document structure is now available.", "Use the section tabs below to inspect each section."],
        json_data=classified_output,
        jump_label="Jump to Sections",
        jump_section="sections",
        accent="accent",
    )
    st.toast("Classified sections are ready. Scroll to the Classified Sections panel.", icon="📄")
    time.sleep(0.05)

    advance("Checking Completeness", 0.52)
    completeness_checker = completeness_module.CompletenessChecker()
    deterministic_result = completeness_checker.check_completeness(classified_output)
    completeness_report = completeness_checker.validate_with_llm(deterministic_result)
    _render_live_panel(
        panels["completeness"],
        "Stage 2",
        "Completeness Check",
        metrics=[("Overall", f"{completeness_report.get('summary', {}).get('overall_score', 0.0):.2f}"), ("Weakest", len(completeness_report.get("summary", {}).get("weakest_sections", [])))],
        summary=[
            "Detailed completeness results are now populated in the completeness tab.",
            "Missing sections: " + (", ".join(completeness_report.get("summary", {}).get("missing_sections", [])) or "None"),
        ],
        json_data=completeness_report,
        jump_label="Jump to Completeness",
        jump_section="completeness",
        accent="warn",
    )
    st.toast("Completeness finished. Open the Completeness section for details.", icon="✅")
    time.sleep(0.05)

    advance("Checking Quality", 0.68)
    quality_assessor = quality_module.QualityAssessor()
    quality_report = quality_assessor.assess_quality(classified_output)
    _render_live_panel(
        panels["quality"],
        "Stage 3",
        "Quality Review",
        metrics=[("Overall", f"{quality_report.get('summary', {}).get('overall_quality', 0.0):.0f}"), ("Sections", len(quality_report.get("sections", [])))],
        summary=[
            "Detailed quality results are now populated in the quality tab.",
            "Strongest sections: " + (", ".join(quality_report.get("summary", {}).get("strongest_sections", [])) or "None"),
        ],
        json_data=quality_report,
        jump_label="Jump to Quality",
        jump_section="quality",
        accent="success",
    )
    st.toast("Quality finished. Open the Quality section for details.", icon="✨")
    time.sleep(0.05)

    advance("Building Features", 0.80)
    features = feature_module.build_features({"completeness": completeness_report, "quality": quality_report})
    _render_live_panel(
        panels["features"],
        "Stage 4",
        "Feature Builder",
        metrics=[("Completeness", f"{features.get('overall_completeness', 0.0):.2f}"), ("Quality", f"{features.get('overall_quality', 0.0):.2f}"), ("Sections", features.get("section_count", 0))],
        summary=["These are the feature signals used by the risk engine.", "They are built from completeness and quality only."],
        json_data=features,
        jump_label="Jump to Features",
        jump_section="features",
        accent="accent",
    )
    st.toast("Features built. Open the Features section to inspect the inputs.", icon="🧩")
    time.sleep(0.05)

    advance("Predicting Risk", 0.93)
    risk_report = risk_module.predict_risk(features)
    report = {
        "classified_sections": classified_output,
        "completeness": completeness_report,
        "quality": quality_report,
        "features": features,
        "risk": risk_report,
    }
    _render_live_panel(
        panels["risk"],
        "Stage 5",
        "Risk Analyzer",
        metrics=[("Risk", risk_report.get("overall_risk", "Unknown")), ("Score", f"{risk_report.get('risk_score', 0.0):.1f}")],
        summary=["The risk panel is now populated with the rule-based score and explanation."],
        json_data=risk_report,
        jump_label="Jump to Risk",
        jump_section="risk",
        accent="danger",
    )
    st.toast("Risk prediction finished. Review the final report below.", icon="📊")
    time.sleep(0.05)

    advance("Report Generated", 1.0)
    completion_slot.empty()
    with completion_slot.container():
        _render_completion_popup(report)
    st.session_state.report_ready = True
    st.toast("Final report generated.", icon="✅")
    return report


def _render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">MDoNER DPR Review Studio</div>
            <h1>Completeness, Quality, Features, and Risk in one view</h1>
            <p>
                This dashboard runs the full DPR pipeline end to end: section detection, classification,
                completeness assessment, quality review, feature building, and rule-based risk scoring with
                LLM explanations. The risk model consumes features only, not raw PDF text.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_top_metrics(report):
    completeness = report.get("completeness", {}).get("summary", {}) if isinstance(report, dict) else {}
    quality = report.get("quality", {}).get("summary", {}) if isinstance(report, dict) else {}
    risk = report.get("risk", {}) if isinstance(report, dict) else {}
    features = report.get("features", {}) if isinstance(report, dict) else {}

    cols = st.columns(4)
    metrics = [
        ("Overall Completeness", completeness.get("overall_score", 0.0), "DPR checklist coverage"),
        ("Overall Quality", quality.get("overall_quality", 0.0), "Writing, depth, and evidence"),
        ("Risk Score", risk.get("risk_score", 0.0), f"{risk.get('overall_risk', 'Unknown')} risk"),
        ("Missing Sections", len(features.get("missing_sections", [])) if isinstance(features, dict) else 0, "Sections not found"),
    ]

    for col, (label, value, note) in zip(cols, metrics):
        with col:
            col.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_overview(report):
    completeness = report.get("completeness", {}).get("summary", {}) if isinstance(report, dict) else {}
    quality = report.get("quality", {}).get("summary", {}) if isinstance(report, dict) else {}
    risk = report.get("risk", {}) if isinstance(report, dict) else {}

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.markdown('<div id="overview"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Executive Summary")
        st.write(
            "The report is assembled from the deterministic completeness rubric, the section quality review, "
            "and a feature-only risk engine. Gemini is used only to explain the scores, not to invent them."
        )
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.write(f"**Overall risk:** {risk.get('overall_risk', 'Unknown')}  ")
        st.write(f"**Confidence:** {risk.get('confidence', 0.0)}")
        top_issues = risk.get("top_issues", []) if isinstance(risk, dict) else []
        if top_issues:
            st.markdown("**Top issues**")
            for item in top_issues:
                st.markdown(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Overall DPR Score")
        _render_score_ring(risk.get("risk_score", 0.0), "Overall DPR Score", f"{risk.get('overall_risk', 'Unknown')} risk")
        badge_class, badge_text = _risk_badge(risk.get("overall_risk", ""))
        st.markdown(
            f"<div style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)


def _render_features(features):
    st.markdown('<div id="features"></div>', unsafe_allow_html=True)
    st.subheader("Feature Builder Output")
    st.caption("These are the exact signals the risk engine uses. They are built from completeness and quality only.")

    cols = st.columns(3)
    feature_cards = [
        ("overall_completeness", features.get("overall_completeness", 0.0), "Aggregated completeness score"),
        ("overall_quality", features.get("overall_quality", 0.0), "Aggregated quality score"),
        ("section_count", features.get("section_count", 0), "Total analyzed sections"),
    ]
    for col, (label, value, note) in zip(cols, feature_cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if features.get("missing_sections"):
        st.markdown("**Missing sections**")
        st.write(", ".join(features.get("missing_sections", [])))

    with st.expander("Show full features JSON", expanded=True):
        _render_full_json(features, "Full features JSON")


def _render_risk(report):
    st.markdown('<div id="risk"></div>', unsafe_allow_html=True)
    st.subheader("Risk Analyzer")
    risk = report.get("risk", {}) if isinstance(report, dict) else {}
    cols = st.columns([1.15, 1, 1, 1], gap="medium")
    with cols[0]:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("<div class='metric-label'>Overall Risk</div>", unsafe_allow_html=True)
        _render_score_ring(risk.get("risk_score", 0.0), "Risk Score", risk.get("overall_risk", "Unknown"))
        badge_class, badge_text = _risk_badge(risk.get("overall_risk", ""))
        st.markdown(f"<div style='text-align:center;'><span class='{badge_class}'>{badge_text}</span></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>Delay Risk</div><div class='metric-value'>{risk.get('delay_risk', 0.0)}%</div><div class='metric-note'>Schedule exposure</div></div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>Cost Risk</div><div class='metric-value'>{risk.get('cost_risk', 0.0)}%</div><div class='metric-note'>Budget exposure</div></div>",
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>Approval Risk</div><div class='metric-value'>{risk.get('approval_risk', 0.0)}%</div><div class='metric-note'>Clearance exposure</div></div>",
            unsafe_allow_html=True,
        )

    recommendations = risk.get("recommendations", []) if isinstance(risk, dict) else []
    if recommendations:
        st.markdown("**Recommendations**")
        for rec in recommendations:
            st.markdown(f"<div class='recommendation-box'><span class='badge badge-success'>✓</span>{rec}</div>", unsafe_allow_html=True)

    reasoning = risk.get("reasoning", "") if isinstance(risk, dict) else ""
    if reasoning:
        st.markdown("**LLM explanation**")
        st.write(reasoning)

    rule_breakdown = risk.get("rule_breakdown", {}) if isinstance(risk, dict) else {}
    if rule_breakdown:
        st.markdown("**Risk breakdown**")
        for key, data in rule_breakdown.items():
            score = data.get("score", 0.0)
            drivers = data.get("drivers", [])
            title = key.replace("_", " ").title()
            st.markdown(
                f"<div class='recommendation-box'><strong>{title}</strong>: {score}%<br><span class='subtle'>{'; '.join(drivers)}</span></div>",
                unsafe_allow_html=True,
            )

    with st.expander("Show risk JSON", expanded=True):
        _render_full_json(risk, "Full risk JSON")


def _render_section_card(index, section, mode="quality"):
    title = section.get("title") or section.get("section") or f"Section {index}"
    category = section.get("category", "")
    content = section.get("content", "")
    completeness_score = section.get("score", section.get("completeness_score", 0.0))
    quality_score = section.get("quality_score", 0.0)
    average_score = (float(completeness_score or 0.0) + float(quality_score or 0.0)) / 2.0

    completeness_badge = _score_badge(float(completeness_score or 0.0))
    quality_badge = _score_badge(float(quality_score or 0.0))
    icon = _score_icon(average_score)

    st.markdown(
        f"""
        <div class="section-card">
            <div class="badge badge-accent">{index:02d}</div>
            <div class="badge badge-accent">{category or 'Uncategorized'}</div>
            <div class="badge {completeness_badge}">Completeness {float(completeness_score or 0.0):.0f}%</div>
            <div class="badge {quality_badge}">Quality {float(quality_score or 0.0):.0f}%</div>
            <h3 style="margin: 0.35rem 0 0.25rem 0; color: var(--ink);">{icon} {title}</h3>
            <p class="subtle" style="margin-top: 0;">{mode.title()} analysis for this section</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='section-summary-grid'>"
        f"<div class='section-mini'><div class='name'>Completeness</div><div class='value'>{float(completeness_score or 0.0):.0f}%</div></div>"
        f"<div class='section-mini'><div class='name'>Quality</div><div class='value'>{float(quality_score or 0.0):.0f}%</div></div>"
        f"<div class='section-mini'><div class='name'>Category</div><div class='value' style='font-size:1.15rem;'>{category or 'Uncategorized'}</div></div>"
        f"<div class='section-mini'><div class='name'>Mode</div><div class='value' style='font-size:1.15rem;'>{mode.title()}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1], gap="large")
    with left:
        if section.get("present"):
            st.markdown("**Present items**")
            for item in section.get("present", []):
                st.markdown(f"- {item.get('item', '')}")
                evidence = item.get("evidence", "")
                if evidence:
                    st.caption(evidence)
        if section.get("strengths"):
            st.markdown("**Strengths**")
            for item in section.get("strengths", []):
                st.markdown(f"- {item}")
        if section.get("issues"):
            st.markdown("**Issues**")
            for item in section.get("issues", []):
                st.markdown(f"- {item}")
    with right:
        if section.get("missing"):
            st.markdown("**Missing items**")
            for item in section.get("missing", []):
                st.markdown(f"- {item.get('item', '')}")
                reason = item.get("reason", "")
                if reason:
                    st.caption(reason)
        if section.get("weaknesses"):
            st.markdown("**Weaknesses**")
            for item in section.get("weaknesses", []):
                st.markdown(f"- {item}")
        if section.get("reason"):
            st.markdown("**Reason**")
            st.write(section.get("reason", ""))

    with st.expander(f"View {title} content"):
        st.text_area("Section text", value=content, height=240, key=f"content_{index}_{mode}")


def _render_sections(report):
    st.markdown('<div id="sections"></div>', unsafe_allow_html=True)
    tabs = st.tabs(["Classified Sections", "Completeness Sections", "Quality Sections"])
    classified = report.get("classified_sections", {}).get("sections", []) if isinstance(report, dict) else []
    completeness = report.get("completeness", {}).get("sections", []) if isinstance(report, dict) else []
    quality = report.get("quality", {}).get("sections", []) if isinstance(report, dict) else []

    with tabs[0]:
        st.caption("Sections as detected and classified from the document structure.")
        for index, section in enumerate(classified, start=1):
            _render_section_card(index, section, mode="classified")

    with tabs[1]:
        st.markdown('<div id="completeness"></div>', unsafe_allow_html=True)
        st.caption("Deterministic completeness scoring, with present and missing items.")
        for index, section in enumerate(completeness, start=1):
            _render_section_card(index, section, mode="completeness")

    with tabs[2]:
        st.markdown('<div id="quality"></div>', unsafe_allow_html=True)
        st.caption("LLM quality review with multi-dimensional scores and reasoning.")
        for index, section in enumerate(quality, start=1):
            _render_section_card(index, section, mode="quality")


def _render_sidebar():
    st.sidebar.title("Analysis Controls")
    st.sidebar.write("Run the full DPR pipeline on a sample file or your own PDF.")

    source = st.sidebar.radio("Input source", ["Sample PDF", "Upload PDF"], index=0)
    uploaded_file = None
    if source == "Upload PDF":
        uploaded_file = st.sidebar.file_uploader("Choose a DPR PDF", type=["pdf"])

    run_clicked = st.sidebar.button("Run full analysis", type="primary", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("Pipeline")
    st.sidebar.write("PDF -> Section Detection -> Classification -> Completeness -> Quality -> Feature Builder -> Risk Analyzer")

    st.sidebar.markdown("---")
    st.sidebar.caption("Report artifacts")
    st.sidebar.write("Final report, feature JSON, and section-level outputs are all included in the dashboard.")

    return source, uploaded_file, run_clicked


def _save_uploaded_pdf(uploaded_file):
    target_dir = APP_DIR / "data" / "raw"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getbuffer())
    return target_path


def main():
    source, uploaded_file, run_clicked = _render_sidebar()
    _render_hero()

    if "report" not in st.session_state:
        st.session_state.report = None
        st.session_state.pdf_path = None
        st.session_state.focus_section = "overview"
        st.session_state.report_ready = False

    if source == "Upload PDF" and uploaded_file is None:
        st.info("Upload a PDF in the sidebar, then run the analysis.")
        return

    if run_clicked:
        pdf_path = _default_pdf_path() if source == "Sample PDF" else _save_uploaded_pdf(uploaded_file)
        loading_slot = st.empty()
        progress_slot = st.progress(0)
        completion_slot = st.empty()
        st.markdown('<div class="panel"><div class="eyebrow">Live Processing</div><h2 style="margin: 0.2rem 0 0.5rem 0;">Watch the current process and the completed batches</h2><div class="subtle">The final report appears only after the last tick.</div></div>', unsafe_allow_html=True)
        live_tabs = st.tabs(["Current Process", "Completed Batches"])
        with live_tabs[0]:
            live_status_slot = st.empty()
        with live_tabs[1]:
            live_col1, live_col2 = st.columns(2)
            panels = {
                "classified": live_col1.container(),
                "completeness": live_col2.container(),
                "quality": live_col1.container(),
                "features": live_col2.container(),
                "risk": st.container(),
            }
        with st.spinner("Running the full DPR pipeline..."):
            st.session_state.report = _run_live_analysis(
                pdf_path,
                live_status_slot,
                progress_slot,
                completion_slot,
                panels,
            )
            st.session_state.pdf_path = str(pdf_path)
            st.session_state.report_ready = True
            st.balloons()

    report = st.session_state.report
    if not report:
        st.markdown(
            '<div class="panel">Select an input and run the analysis to see the final report. The output will include the score ring, section cards, recommendations, workflow steps, and download button.</div>',
            unsafe_allow_html=True,
        )
        return

    _render_navigation_chips()
    _render_quick_toc()

    st.subheader("Workflow")
    workflow_steps = ["Reading PDF", "Finding TOC", "Classifying Sections", "Checking Completeness", "Checking Quality", "Building Features", "Predicting Risk", "Report Generated"]
    st.markdown("<div class='completed-strip'>" + "".join(f"<span class='completed-chip'>✓ {step}</span>" for step in workflow_steps) + "</div>", unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if st.session_state.get("focus_section") and st.session_state.focus_section != "overview":
        focus_label = st.session_state.focus_section.title()
        st.info(f"Focus set to {focus_label}. Use the section tabs below to inspect that area.")

    _render_top_metrics(report)
    _render_overview(report)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.subheader("Completed Batches")
    st.caption("Select a tab to inspect each finished stage in a compact view.")
    _render_stage_tabs(report)

    recommendations = report.get("risk", {}).get("recommendations", []) if isinstance(report, dict) else []
    if recommendations:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.subheader("AI Recommendations")
        for rec in recommendations:
            st.markdown(
                f"<div class='recommendation-box'><span class='badge badge-accent'>✓</span>{rec}</div>",
                unsafe_allow_html=True,
            )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.subheader("Download")
    st.download_button(
        "Download AI Assessment Report",
        data=_build_pdf_report_bytes(report),
        file_name="dpr_ai_assessment_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    with st.expander("View final JSON", expanded=True):
        _render_full_json(report, "Final report JSON")

    if st.session_state.get("report_ready"):
        _render_completion_popup(report)


if __name__ == "__main__":
    main()
