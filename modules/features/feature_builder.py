from collections import defaultdict
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_DIR / "outputs"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.analysis.completeness_checker import CompletenessChecker
from modules.analysis.quality_checker import QualityAssessor
from modules.classification.section_classifier import SectionClassifier


def _normalize_sections(report):
    if not isinstance(report, dict):
        return []
    sections = report.get("sections", [])
    return sections if isinstance(sections, list) else []


def _section_name(section):
    return str(section.get("section") or section.get("title") or "").strip()


def _section_category(section):
    return str(section.get("category", "")).strip()


def build_features(data):
    """Build risk features from completeness and quality reports only."""
    completeness_report = data.get("completeness", {}) if isinstance(data, dict) else {}
    quality_report = data.get("quality", {}) if isinstance(data, dict) else {}

    completeness_sections = _normalize_sections(completeness_report)
    quality_sections = _normalize_sections(quality_report)

    completeness_by_section = {_section_name(section): section for section in completeness_sections}
    quality_by_section = {_section_name(section): section for section in quality_sections}

    section_names = list(completeness_by_section.keys() or quality_by_section.keys())
    missing_sections = list(completeness_report.get("summary", {}).get("missing_sections", [])) if isinstance(completeness_report, dict) else []

    category_scores = defaultdict(list)
    for section in quality_sections:
        category = _section_category(section)
        if category:
            category_scores[category.lower()].append(float(section.get("quality_score", 0) or 0))

    averaged_category_scores = {
        f"{category}_quality": round(sum(scores) / len(scores), 2) if scores else 0.0
        for category, scores in category_scores.items()
    }

    features = {
        "overall_completeness": float(completeness_report.get("summary", {}).get("overall_score", 0.0) or 0.0),
        "overall_quality": float(quality_report.get("summary", {}).get("overall_quality", 0.0) or 0.0),
        "missing_sections": missing_sections,
        "section_count": len(section_names),
        "quality_section_count": len(quality_sections),
        "completeness_section_count": len(completeness_sections),
    }

    features.update(averaged_category_scores)

    for name in section_names:
        completeness_section = completeness_by_section.get(name, {})
        quality_section = quality_by_section.get(name, {})
        key = name.lower().replace(" ", "_")
        features[f"{key}_completeness"] = float(completeness_section.get("score", 0.0) or 0.0)
        features[f"{key}_quality"] = float(quality_section.get("quality_score", 0.0) or 0.0)

    return features


def build_features_from_reports(completeness_report, quality_report):
    return build_features({"completeness": completeness_report, "quality": quality_report})


def build_features_from_pdf(pdf_path):
    classifier = SectionClassifier()
    classified_output = classifier.final_json(pdf_path)

    completeness_checker = CompletenessChecker()
    deterministic_result = completeness_checker.check_completeness(classified_output)
    completeness_report = completeness_checker.validate_with_llm(deterministic_result)

    quality_assessor = QualityAssessor()
    quality_report = quality_assessor.assess_quality(classified_output)

    return build_features_from_reports(completeness_report, quality_report)


def _default_pdf_path():
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    return pdf_path


def main():
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _default_pdf_path()
    features = build_features_from_pdf(pdf_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "features.json"
    output_path.write_text(json.dumps(features, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(features, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
