import os
import sys
from pathlib import Path
import json
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

from section_classifier import SectionClassifier

load_dotenv()


class QualityAssessor:
    def __init__(self):
        self.model_name = config.MODEL_NAME
        self.google_api_key = config.GOOGLE_API_KEY
        self.section_classifier = SectionClassifier()
        self.retry_config = types.HttpRetryOptions(
            attempts=3,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )

        self.assistant_agent = LlmAgent(
            name="dpr_quality_assessor",
            model=Gemini(
                model=self.model_name,
                retry=self.retry_config,
            ),
            description=(
                "Acts as an expert DPR quality review agent. It evaluates the writing quality, technical depth, "
                "clarity, consistency, organization, professionalism, and evidence quality of already classified DPR sections."
            ),
            instruction="""
            You are an expert Government DPR Quality Assessment AI working for MDoNER.

            You receive one or more classified DPR sections.

            Each section already contains:
            - title
            - category
            - content

            Your task is NOT to check whether mandatory items exist.
            The Completeness Checker has already done that.

            Instead, evaluate ONLY the quality of the available content.

            Assess every section using the following criteria:

            1. Clarity
            - Is the writing understandable?
            - Are technical explanations easy to follow?

            2. Technical Depth
            - Does the section provide enough engineering, financial, or technical detail?
            - Are explanations superficial or comprehensive?

            3. Consistency
            - Are there contradictions?
            - Do numbers, statements, and descriptions remain consistent throughout the section?

            4. Organization
            - Is the information logically structured?
            - Does the section flow naturally?

            5. Professionalism
            - Is the writing suitable for an official government DPR?

            6. Evidence & Justification
            - Are claims supported with calculations, references, standards, or reasoning where appropriate?

            Return ONLY valid JSON.

            Output Schema

            {
              "sections": [
                {
                  "section": "string",
                  "category": "string",
                  "quality_score": 0-100,
                  "clarity": 0-100,
                  "technical_depth": 0-100,
                  "consistency": 0-100,
                  "organization": 0-100,
                  "professionalism": 0-100,
                  "evidence": 0-100,
                  "strengths": ["..."],
                  "weaknesses": ["..."],
                  "issues": ["..."],
                  "reason": "..."
                }
              ],
              "summary": {
                "overall_quality": 0-100,
                "strongest_sections": [...],
                "weakest_sections": [...]
              }
            }

            Rules

            - Never invent information.
            - Judge only the provided content.
            - If a section is short but clear, score clarity high but technical depth lower.
            - Keep explanations concise.
            - Return JSON only.
            """,
        )

        self.runner = InMemoryRunner(agent=self.assistant_agent)

    def _normalize_sections(self, classifier_output):
        if isinstance(classifier_output, dict):
            sections = classifier_output.get("sections", [])
            if isinstance(sections, list):
                return sections
        if isinstance(classifier_output, list):
            return classifier_output
        return []

    def _build_payload(self, classifier_output):
        sections = self._normalize_sections(classifier_output)
        metadata = classifier_output.get("metadata", {}) if isinstance(classifier_output, dict) else {}
        return {
            "metadata": metadata,
            "sections": [
                {
                    "title": section.get("title", ""),
                    "category": section.get("category", ""),
                    "content": section.get("content", ""),
                    "start_page": section.get("start_page", 0),
                    "end_page": section.get("end_page", 0),
                }
                for section in sections
                if isinstance(section, dict)
            ],
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

        return {"sections": [], "summary": {}}

    def _build_fallback_report(self, classifier_output):
        sections = self._normalize_sections(classifier_output)
        fallback_sections = []

        for section in sections:
            title = str(section.get("title", "")).strip()
            category = str(section.get("category", "")).strip()
            fallback_sections.append(
                {
                    "section": title,
                    "category": category,
                    "quality_score": 0,
                    "clarity": 0,
                    "technical_depth": 0,
                    "consistency": 0,
                    "organization": 0,
                    "professionalism": 0,
                    "evidence": 0,
                    "strengths": [],
                    "weaknesses": ["Quality assessment could not be generated from the model response."],
                    "issues": ["LLM response could not be parsed."],
                    "reason": "Fallback report generated because the quality model response was empty or invalid.",
                }
            )

        return {
            "sections": fallback_sections,
            "summary": {
                "overall_quality": 0,
                "strongest_sections": [],
                "weakest_sections": [section.get("section", "") for section in fallback_sections],
            },
        }

    def assess_quality(self, classifier_output):
        payload = self._build_payload(classifier_output)
        query = (
            "Assess the following classified DPR sections for quality and return only valid JSON.\n\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        response = asyncio.run(self.runner.run_debug(query))
        raw_text = response[-1].content.parts[0].text
        parsed = self._parse_agent_response(raw_text)
        if not parsed.get("sections"):
            return self._build_fallback_report(classifier_output)
        return parsed

    def final_json(self, pdf_path):
        classified_output = self.section_classifier.final_json(pdf_path)
        return self.assess_quality(classified_output)


def assess_quality(data):
    assessor = QualityAssessor()
    if isinstance(data, (str, Path)):
        return assessor.final_json(data)
    return assessor.assess_quality(data)


def main():
    assessor = QualityAssessor()
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    print("Response from QualityAssessor:", assessor.final_json(pdf_path))


if __name__ == "__main__":
    main()
