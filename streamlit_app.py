import json
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
MODULES_DIR = APP_DIR / "modules"
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from completness_check import CompletenessChecker


st.set_page_config(page_title="DPR Completeness Demo", page_icon="📄", layout="wide")


def _load_json_file(uploaded_file):
    raw = uploaded_file.read().decode("utf-8")
    return json.loads(raw)


def _render_summary(summary):
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Score", f"{summary.get('overall_score', 0.0)}")
    col2.metric("Average Score", f"{summary.get('average_score', 0.0)}")
    col3.metric("Weakest Sections", str(len(summary.get("weakest_sections", []))))


def _render_sections(sections):
    for index, section in enumerate(sections, start=1):
        title = section.get("section", f"Section {index}")
        category = section.get("category", "")
        score = section.get("score", 0.0)
        present = section.get("present", [])
        missing = section.get("missing", [])
        content = section.get("content", "")

        with st.container(border=True):
            st.subheader(f"{index}. {title}")
            st.caption(f"Category: {category} | Score: {score}")

            left, right = st.columns(2)
            with left:
                st.markdown("**Present items**")
                if present:
                    for item in present:
                        st.markdown(f"- **{item.get('item', '')}**")
                        evidence = item.get("evidence", "")
                        if evidence:
                            st.code(evidence)
                else:
                    st.write("None")

            with right:
                st.markdown("**Missing items**")
                if missing:
                    for item in missing:
                        st.markdown(f"- **{item.get('item', '')}**")
                        reason = item.get("reason", "")
                        if reason:
                            st.write(reason)
                else:
                    st.write("None")

            with st.expander("Show content"):
                st.text_area(
                    "Section content",
                    value=content,
                    height=260,
                    key=f"section_content_{index}",
                )


def main():
    st.title("DPR Completeness Demo")
    st.write("Upload a report PDF or a saved JSON output, then review the results in order.")

    mode = st.radio("Input type", ["PDF", "JSON output"], horizontal=True)

    uploaded_file = None
    if mode == "PDF":
        uploaded_file = st.file_uploader("Upload a DPR PDF", type=["pdf"])
    else:
        uploaded_file = st.file_uploader("Upload a saved JSON result", type=["json"])

    if uploaded_file is None:
        st.info("Upload a file to begin.")
        return

    if mode == "JSON output":
        result = _load_json_file(uploaded_file)
    else:
        temp_path = APP_DIR / "data" / "raw" / uploaded_file.name
        temp_path.write_bytes(uploaded_file.getbuffer())
        checker = CompletenessChecker()
        result = checker.final_chat(temp_path)

    sections = result.get("sections", []) if isinstance(result, dict) else []
    summary = result.get("summary", {}) if isinstance(result, dict) else {}

    st.success(f"Loaded {len(sections)} sections")
    _render_summary(summary)

    st.markdown("---")
    _render_sections(sections)


if __name__ == "__main__":
    main()