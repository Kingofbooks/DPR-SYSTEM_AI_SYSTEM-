import json
import os
import sys
from pathlib import Path
import asyncio

APP_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = APP_DIR / "modules"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))

from dotenv import load_dotenv
from config import config
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

from feature_builder import build_features_from_pdf

load_dotenv()


class RiskAnalyzer:
    def __init__(self):
        self.model_name = config.MODEL_NAME
        self.google_api_key = config.GOOGLE_API_KEY
        self.retry_config = types.HttpRetryOptions(
            attempts=3,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )
        self.assistant_agent = LlmAgent(
            name="dpr_risk_analyzer",
            model=Gemini(
                model=self.model_name,
                retry=self.retry_config,
            ),
            description="Explains DPR risk using only precomputed document features and rule-engine outputs.",
            instruction="""
            You are an MDoNER DPR Risk Assessment Officer.

            You receive precomputed risk features and rule-based score breakdowns only.
            You do NOT read PDFs or raw section text.

            Your job is to explain why the provided risk scores were assigned.
            Do not change the numeric scores.
            Do not introduce new facts.

            Return ONLY valid JSON.

            Output schema:
            {
              "reasoning": "string"
            }

            Rules:
            - Explain only the supplied risk drivers.
            - Keep the explanation concise and defensible.
            - Return JSON only.
            """,
        )
        self.runner = InMemoryRunner(agent=self.assistant_agent)

    def _feature_value(self, features, key, default=0.0):
        if not isinstance(features, dict):
            return default
        value = features.get(key, default)
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return default

    def _feature_present(self, features, key):
        return self._feature_value(features, key, 0.0) > 0.0

    def _clip(self, value):
        return max(0.0, min(100.0, round(value, 2)))

    def _category_score(self, features, category):
        return self._feature_value(features, f"{category}_quality", self._feature_value(features, f"{category}_completeness", 0.0))

    def _section_score(self, features, name):
        return self._feature_value(features, f"{name}_quality", self._feature_value(features, f"{name}_completeness", 0.0))

    def _score_delay_risk(self, features):
        score = 14.0
        drivers = []

        timeline_quality = self._category_score(features, "timeline")
        technical_quality = self._category_score(features, "technical")
        overall_completeness = self._feature_value(features, "overall_completeness", 0.0)
        overall_quality = self._feature_value(features, "overall_quality", 0.0)
        timeline_completeness = self._feature_value(features, "timeline_completeness", 0.0)
        missing_sections = set(str(item).strip().lower() for item in features.get("missing_sections", []) if item)

        if "timeline" in missing_sections:
            score += 28.0
            drivers.append("Timeline section is missing.")
        if timeline_quality and timeline_quality < 70:
            delta = (70 - timeline_quality) * 0.55
            score += delta
            drivers.append(f"Timeline quality is {timeline_quality:.0f}.")
        if timeline_completeness and timeline_completeness < 70:
            delta = (70 - timeline_completeness) * 0.35
            score += delta
            drivers.append(f"Timeline completeness is {timeline_completeness:.0f}.")
        if technical_quality and technical_quality < 70:
            delta = (70 - technical_quality) * 0.30
            score += delta
            drivers.append(f"Technical quality is {technical_quality:.0f}.")
        if overall_completeness and overall_completeness < 60:
            delta = (60 - overall_completeness) * 0.20
            score += delta
            drivers.append(f"Overall completeness is {overall_completeness:.0f}.")
        if overall_quality and overall_quality < 60:
            delta = (60 - overall_quality) * 0.10
            score += delta
            drivers.append(f"Overall quality is {overall_quality:.0f}.")

        return self._clip(score), drivers or ["Timeline and implementation signals are adequate."]

    def _score_cost_risk(self, features):
        score = 16.0
        drivers = []

        budget_quality = self._category_score(features, "budget")
        financial_quality = self._category_score(features, "financial")
        budget_completeness = self._feature_value(features, "budget_completeness", 0.0)
        financial_completeness = self._feature_value(features, "financial_completeness", 0.0)
        overall_completeness = self._feature_value(features, "overall_completeness", 0.0)
        missing_sections = set(str(item).strip().lower() for item in features.get("missing_sections", []) if item)

        if {"budget", "financial"} & missing_sections:
            score += 22.0
            drivers.append("Budget or financial section is missing.")
        if budget_quality and budget_quality < 70:
            delta = (70 - budget_quality) * 0.50
            score += delta
            drivers.append(f"Budget quality is {budget_quality:.0f}.")
        if financial_quality and financial_quality < 70:
            delta = (70 - financial_quality) * 0.45
            score += delta
            drivers.append(f"Financial quality is {financial_quality:.0f}.")
        if budget_completeness and budget_completeness < 70:
            delta = (70 - budget_completeness) * 0.25
            score += delta
            drivers.append(f"Budget completeness is {budget_completeness:.0f}.")
        if financial_completeness and financial_completeness < 70:
            delta = (70 - financial_completeness) * 0.25
            score += delta
            drivers.append(f"Financial completeness is {financial_completeness:.0f}.")
        if overall_completeness and overall_completeness < 60:
            score += (60 - overall_completeness) * 0.10

        return self._clip(score), drivers or ["Cost structure appears moderately supported."]

    def _score_approval_risk(self, features):
        score = 14.0
        drivers = []

        legal_quality = self._category_score(features, "legal")
        environmental_quality = self._category_score(features, "environmental")
        risk_quality = self._category_score(features, "risk")
        legal_completeness = self._feature_value(features, "legal_completeness", 0.0)
        environmental_completeness = self._feature_value(features, "environmental_completeness", 0.0)
        overall_quality = self._feature_value(features, "overall_quality", 0.0)
        missing_sections = set(str(item).strip().lower() for item in features.get("missing_sections", []) if item)

        if "legal" in missing_sections:
            score += 24.0
            drivers.append("Legal section is missing.")
        if "environmental" in missing_sections:
            score += 20.0
            drivers.append("Environmental section is missing.")
        if legal_quality and legal_quality < 70:
            delta = (70 - legal_quality) * 0.45
            score += delta
            drivers.append(f"Legal quality is {legal_quality:.0f}.")
        if environmental_quality and environmental_quality < 70:
            delta = (70 - environmental_quality) * 0.40
            score += delta
            drivers.append(f"Environmental quality is {environmental_quality:.0f}.")
        if risk_quality and risk_quality < 70:
            delta = (70 - risk_quality) * 0.25
            score += delta
            drivers.append(f"Risk quality is {risk_quality:.0f}.")
        if legal_completeness and legal_completeness < 70:
            score += (70 - legal_completeness) * 0.20
        if environmental_completeness and environmental_completeness < 70:
            score += (70 - environmental_completeness) * 0.20
        if overall_quality and overall_quality < 60:
            score += (60 - overall_quality) * 0.10

        return self._clip(score), drivers or ["Approval-related sections are moderately supported."]

    def _overall_risk_label(self, score):
        if score >= 70:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"

    def _build_rule_report(self, features):
        delay_risk, delay_drivers = self._score_delay_risk(features)
        cost_risk, cost_drivers = self._score_cost_risk(features)
        approval_risk, approval_drivers = self._score_approval_risk(features)

        overall_score = self._clip((delay_risk * 0.4) + (cost_risk * 0.35) + (approval_risk * 0.25))
        overall_risk = self._overall_risk_label(overall_score)

        driver_pool = [
            ("delay_risk", delay_risk, delay_drivers),
            ("cost_risk", cost_risk, cost_drivers),
            ("approval_risk", approval_risk, approval_drivers),
        ]
        driver_pool.sort(key=lambda item: item[1], reverse=True)

        top_issues = []
        recommendations = []
        seen = set()
        recommendation_map = {
            "Timeline section is missing.": "Add a clear implementation schedule and milestones.",
            "Budget or financial section is missing.": "Add an itemized budget and financing summary.",
            "Legal section is missing.": "Add approvals, statutory compliance, and legal references.",
            "Environmental section is missing.": "Add environmental impacts and mitigation measures.",
            "Timeline quality is": "Strengthen sequencing, milestones, and delivery dates.",
            "Timeline completeness is": "Add missing schedule details and dependencies.",
            "Technical quality is": "Expand technical method, specifications, and implementation detail.",
            "Budget quality is": "Provide a clearer cost breakup and supporting calculations.",
            "Financial quality is": "Provide financing source, assumptions, and cost justification.",
            "Legal quality is": "Clarify approvals and regulatory backing.",
            "Environmental quality is": "Add impact assessment and mitigation detail.",
            "Risk quality is": "Add mitigation and contingency planning.",
        }

        for _, _, drivers in driver_pool:
            for driver in drivers:
                if driver not in seen:
                    top_issues.append(driver)
                    seen.add(driver)

                recommendation = None
                for key, value in recommendation_map.items():
                    if driver.startswith(key):
                        recommendation = value
                        break
                if recommendation and recommendation not in recommendations:
                    recommendations.append(recommendation)

        if not recommendations:
            recommendations = ["Maintain current document structure and tighten supporting evidence where needed."]

        confidence = self._clip(100.0 - min(35.0, abs(overall_score - 50.0) * 0.7))

        return {
            "overall_risk": overall_risk,
            "risk_score": overall_score,
            "delay_risk": delay_risk,
            "cost_risk": cost_risk,
            "approval_risk": approval_risk,
            "confidence": confidence,
            "top_issues": top_issues[:5],
            "recommendations": recommendations[:5],
            "priority_order": [item[0] for item in driver_pool],
            "feature_summary": {
                "overall_completeness": self._feature_value(features, "overall_completeness", 0.0),
                "overall_quality": self._feature_value(features, "overall_quality", 0.0),
                "missing_sections": features.get("missing_sections", []) if isinstance(features, dict) else [],
            },
            "rule_breakdown": {
                "delay_risk": {"score": delay_risk, "drivers": delay_drivers},
                "cost_risk": {"score": cost_risk, "drivers": cost_drivers},
                "approval_risk": {"score": approval_risk, "drivers": approval_drivers},
            },
        }

    def _parse_explanation(self, raw_text):
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and isinstance(parsed.get("reasoning"), str):
                    return parsed["reasoning"].strip()
            except json.JSONDecodeError:
                pass
        return cleaned or "The risk score was derived from rule-based feature thresholds."

    def _build_explanation_payload(self, rule_report):
        return {
            "overall_risk": rule_report.get("overall_risk", "Medium"),
            "risk_score": rule_report.get("risk_score", 0.0),
            "delay_risk": rule_report.get("delay_risk", 0.0),
            "cost_risk": rule_report.get("cost_risk", 0.0),
            "approval_risk": rule_report.get("approval_risk", 0.0),
            "top_issues": rule_report.get("top_issues", []),
            "recommendations": rule_report.get("recommendations", []),
            "priority_order": rule_report.get("priority_order", []),
            "feature_summary": rule_report.get("feature_summary", {}),
            "rule_breakdown": rule_report.get("rule_breakdown", {}),
        }

    def _parse_agent_response(self, raw_text):
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {"reasoning": "The risk score was derived from rule-based feature thresholds."}

    def analyze(self, features):
        payload = features if isinstance(features, dict) else {}
        rule_report = self._build_rule_report(payload)
        query = (
            "Explain the following DPR risk assessment using only the supplied scores and drivers.\n\n"
            f"{json.dumps(self._build_explanation_payload(rule_report), ensure_ascii=False)}"
        )
        response = asyncio.run(self.runner.run_debug(query))
        raw_text = response[-1].content.parts[0].text
        rule_report["reasoning"] = self._parse_explanation(raw_text)
        return rule_report


def predict_risk(features):
    """Analyze risk from feature inputs only."""
    analyzer = RiskAnalyzer()
    return analyzer.analyze(features)


def _default_pdf_path():
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    return pdf_path


def _default_features_path():
    return APP_DIR / "outputs" / "features.json"


def _load_features_from_json(path):
    feature_path = Path(path)
    if not feature_path.exists():
        return {}
    try:
        return json.loads(feature_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _default_features_path()

    if input_path.suffix.lower() == ".json" and input_path.exists():
        features = _load_features_from_json(input_path)
    else:
        pdf_path = input_path if input_path.exists() else _default_pdf_path()
        features = build_features_from_pdf(pdf_path)

    risk_report = predict_risk(features)
    print(json.dumps(risk_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
