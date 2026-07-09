import importlib
import json
import sys
from pathlib import Path

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
    return importlib.import_module("pipeline.pipeline")


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

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Executive Summary")
        st.write(
            "The report is assembled from the deterministic completeness rubric, the section quality review, "
            "and a feature-only risk engine. Gemini is used only to explain the scores, not to invent them."
        )
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.write(
            f"**Overall risk:** {risk.get('overall_risk', 'Unknown')}  \n"
            f"**Risk score:** {risk.get('risk_score', 0.0)}  \n"
            f"**Confidence:** {risk.get('confidence', 0.0)}"
        )
        top_issues = risk.get("top_issues", []) if isinstance(risk, dict) else []
        if top_issues:
            st.markdown("**Top issues**")
            for item in top_issues:
                st.markdown(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Score Snapshot")
        st.metric("Completeness", f"{completeness.get('overall_score', 0.0)}")
        st.metric("Quality", f"{quality.get('overall_quality', 0.0)}")
        st.metric("Risk", f"{risk.get('risk_score', 0.0)}")
        st.markdown('</div>', unsafe_allow_html=True)


def _render_features(features):
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

    with st.expander("Show full features JSON"):
        st.json(features)


def _render_risk(report):
    st.subheader("Risk Analyzer")
    risk = report.get("risk", {}) if isinstance(report, dict) else {}
    cols = st.columns(4)
    cards = [
        ("Overall Risk", risk.get("overall_risk", "Unknown"), "Rule-engine output"),
        ("Delay Risk", risk.get("delay_risk", 0.0), "Schedule exposure"),
        ("Cost Risk", risk.get("cost_risk", 0.0), "Budget exposure"),
        ("Approval Risk", risk.get("approval_risk", 0.0), "Clearance exposure"),
    ]
    for col, (label, value, note) in zip(cols, cards):
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

    recommendations = risk.get("recommendations", []) if isinstance(risk, dict) else []
    if recommendations:
        st.markdown("**Recommendations**")
        for rec in recommendations:
            st.markdown(f"- {rec}")

    reasoning = risk.get("reasoning", "") if isinstance(risk, dict) else ""
    if reasoning:
        st.markdown("**LLM explanation**")
        st.write(reasoning)

    with st.expander("Show risk JSON"):
        st.json(risk)


def _render_section_card(index, section, mode="quality"):
    title = section.get("title") or section.get("section") or f"Section {index}"
    category = section.get("category", "")
    content = section.get("content", "")
    completeness_score = section.get("score", section.get("completeness_score", 0.0))
    quality_score = section.get("quality_score", 0.0)

    completeness_badge = _score_badge(float(completeness_score or 0.0))
    quality_badge = _score_badge(float(quality_score or 0.0))

    st.markdown(
        f"""
        <div class="section-card">
            <div class="badge badge-accent">{index:02d}</div>
            <div class="badge badge-accent">{category or 'Uncategorized'}</div>
            <div class="badge {completeness_badge}">Completeness {completeness_score}</div>
            <div class="badge {quality_badge}">Quality {quality_score}</div>
            <h3 style="margin: 0.35rem 0 0.25rem 0; color: var(--ink);">{title}</h3>
            <p class="subtle" style="margin-top: 0;">{mode.title()} analysis for this section</p>
        </div>
        """,
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
    tabs = st.tabs(["Classified Sections", "Completeness Sections", "Quality Sections"])
    classified = report.get("classified_sections", {}).get("sections", []) if isinstance(report, dict) else []
    completeness = report.get("completeness", {}).get("sections", []) if isinstance(report, dict) else []
    quality = report.get("quality", {}).get("sections", []) if isinstance(report, dict) else []

    with tabs[0]:
        st.caption("Sections as detected and classified from the document structure.")
        for index, section in enumerate(classified, start=1):
            _render_section_card(index, section, mode="classified")

    with tabs[1]:
        st.caption("Deterministic completeness scoring, with present and missing items.")
        for index, section in enumerate(completeness, start=1):
            _render_section_card(index, section, mode="completeness")

    with tabs[2]:
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

    if source == "Upload PDF" and uploaded_file is None:
        st.info("Upload a PDF in the sidebar, then run the analysis.")
        return

    if "report" not in st.session_state:
        st.session_state.report = None
        st.session_state.pdf_path = None

    if run_clicked:
        pdf_path = _default_pdf_path() if source == "Sample PDF" else _save_uploaded_pdf(uploaded_file)
        with st.spinner("Running the full DPR pipeline..."):
            st.session_state.report = _run_full_analysis(pdf_path)
            st.session_state.pdf_path = str(pdf_path)

    report = st.session_state.report
    if not report:
        st.markdown('<div class="panel">Select an input and run the analysis to see the final report.</div>', unsafe_allow_html=True)
        return

    _render_top_metrics(report)
    _render_overview(report)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.subheader("Pipeline Outputs")
    _render_sections(report)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    _render_features(report.get("features", {}))

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    _render_risk(report)

    with st.expander("Download final JSON"):
        st.download_button(
            "Download report JSON",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name="dpr_final_report.json",
            mime="application/json",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
