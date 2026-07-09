import json
import importlib
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = APP_DIR / "modules"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))

def _default_pdf_path():
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    return pdf_path


def _build_risk_features(completeness_report, quality_report):
    feature_module = importlib.import_module("modules.feature_builder")
    return feature_module.build_features({"completeness": completeness_report, "quality": quality_report})


def run_pipeline(pdf_path=None):
    pdf_path = Path(pdf_path) if pdf_path else _default_pdf_path()

    section_classifier_module = importlib.import_module("modules.section_classifier")
    completeness_module = importlib.import_module("modules.completness_check")
    quality_module = importlib.import_module("modules.quality_assessor")
    feature_module = importlib.import_module("modules.feature_builder")
    risk_module = importlib.import_module("modules.risk_predictor")

    SectionClassifier = section_classifier_module.SectionClassifier
    CompletenessChecker = completeness_module.CompletenessChecker
    QualityAssessor = quality_module.QualityAssessor
    build_features = feature_module.build_features
    predict_risk = risk_module.predict_risk

    classifier = SectionClassifier()
    classified_output = classifier.final_json(pdf_path)

    completeness_checker = CompletenessChecker()
    deterministic_result = completeness_checker.check_completeness(classified_output)
    completeness_report = completeness_checker.validate_with_llm(deterministic_result)

    quality_assessor = QualityAssessor()
    quality_report = quality_assessor.assess_quality(classified_output)

    risk_features = _build_risk_features(completeness_report, quality_report)
    risk_report = predict_risk(risk_features)

    combined_report = {
        "classified_sections": classified_output,
        "completeness": completeness_report,
        "quality": quality_report,
        "features": risk_features,
        "risk": risk_report,
    }

    print(json.dumps(combined_report, ensure_ascii=False, indent=2))
    return combined_report
