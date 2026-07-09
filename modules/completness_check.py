import os
import sys
from pathlib import Path
import json
import re

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types
from section_classifier import SectionClassifier
from config import config
import asyncio

load_dotenv()


class CompletenessChecker:
    def __init__(self, rules_path=None):
        self.rules_path = Path(rules_path or APP_DIR / "config" / "completeness_rules.yaml")
        self.required_sections = []
        self.optional_sections = []
        self.weights = {}
        self.section_checklists = {
            "Introduction": [
                {"item": "Project background", "weight": 1, "keywords": ["background", "project background"]},
                {"item": "Objectives", "weight": 1, "keywords": ["objective", "objectives"]},
                {"item": "Need of project", "weight": 1, "keywords": ["need of project", "need for the project", "requirement"]},
                {"item": "Location", "weight": 1, "keywords": ["location", "site", "district", "village", "town"]},
                {"item": "Scope", "weight": 1, "keywords": ["scope", "scope of work"]},
                {"item": "Stakeholders", "weight": 1, "keywords": ["stakeholder", "stakeholders", "beneficiary", "beneficiaries"]},
            ],
            "Objectives": [
                {"item": "Primary objective", "weight": 2, "keywords": ["objective", "goal", "aim"]},
                {"item": "Measurable outcomes", "weight": 1, "keywords": ["outcome", "result", "deliverable"]},
            ],
            "Technical": [
                {"item": "Technical approach", "weight": 2, "keywords": ["technical", "method", "design", "approach"]},
                {"item": "Specifications", "weight": 1, "keywords": ["specification", "specifications", "standards"]},
                {"item": "Implementation details", "weight": 1, "keywords": ["implementation", "execution", "process"]},
            ],
            "Financial": [
                {"item": "Cost estimate", "weight": 2, "keywords": ["cost", "estimate", "financial"]},
                {"item": "Funding source", "weight": 1, "keywords": ["funding", "source", "budget"]},
                {"item": "Breakup", "weight": 1, "keywords": ["breakup", "breakdown", "component"]},
            ],
            "Budget": [
                {"item": "Civil cost", "weight": 2, "keywords": ["civil cost", "civil works", "construction cost"]},
                {"item": "Plant equipment cost", "weight": 2, "keywords": ["plant equipment", "equipment cost", "machinery"]},
                {"item": "Operating cost", "weight": 2, "keywords": ["operating cost", "opex", "operation"]},
            ],
            "Timeline": [
                {"item": "Project phases", "weight": 1, "keywords": ["phase", "phases", "milestone"]},
                {"item": "Schedule", "weight": 2, "keywords": ["timeline", "schedule", "duration", "month"]},
            ],
            "Risk": [
                {"item": "Risk identification", "weight": 2, "keywords": ["risk", "issue", "challenge"]},
                {"item": "Mitigation plan", "weight": 2, "keywords": ["mitigation", "control", "manage"]},
            ],
            "Environmental": [
                {"item": "Environmental impact", "weight": 2, "keywords": ["environmental", "impact", "ecology"]},
                {"item": "Mitigation measures", "weight": 2, "keywords": ["mitigation", "pollution", "waste"]},
            ],
            "Legal": [
                {"item": "Approvals", "weight": 2, "keywords": ["legal", "approval", "permission", "compliance"]},
                {"item": "Regulatory requirements", "weight": 2, "keywords": ["regulation", "law", "policy", "act"]},
            ],
        }
        self.load_rules()
        self.retry_config = types.HttpRetryOptions(
                attempts=3,
                exp_base=7,
                initial_delay=1,
                http_status_codes=[429, 500, 503, 504],
            )
        self.validator_agent = LlmAgent(
                name="completeness_validator",
                model=Gemini(model=config.MODEL_NAME, retry=self.retry_config),
                description="Validates deterministic section completeness results and returns a structured final report.",
                instruction="""
                    You are a DPR completeness validator.

                    You receive section-by-section deterministic checklist results.
                    The input JSON contains:
                    - sections: an array of evaluated sections
                    - summary: deterministic summary metrics
                    - input_section_count: how many sections were evaluated

                    Each section already includes:
                    - section
                    - category
                    - expected_items
                    - present
                    - missing
                    - content
                    - score
                    - confidence

                    Your job is to return a clean final JSON report only.

                    Rules:
                    1. Do not invent missing items.
                    2. Use the provided evidence and checklist results only.
                    3. Keep scores numeric.
                    4. Keep the output valid JSON only.
                    5. Return exactly one output section for every input section, in the same order.
                    6. Never return an empty sections array when input_section_count is greater than 0.

                    Output schema:
                    {
                        "sections": [
                            {
                                "section": "string",
                                "category": "string",
                                "score": number,
                                "present": [
                                    {"item": "string", "evidence": "string", "weight": number}
                                ],
                                "missing": [
                                    {"item": "string", "reason": "string", "weight": number}
                                ],
                                "reason": "string"
                            }
                        ],
                        "summary": {
                            "overall_score": number,
                            "average_score": number,
                            "weakest_sections": ["string"],
                            "present_sections": ["string"],
                            "missing_sections": ["string"]
                        }
                    }
                """,
                )
        self.validator_runner = InMemoryRunner(agent=self.validator_agent)

    def load_rules(self):
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {self.rules_path}")

        text = self.rules_path.read_text(encoding="utf-8")
        self._parse_simple_yaml(text)

    def _parse_simple_yaml(self, text):
        current_section = None

        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            if line.startswith("required_sections:"):
                current_section = "required_sections"
                continue
            if line.startswith("optional_sections:"):
                current_section = "optional_sections"
                continue
            if line.startswith("weights:"):
                current_section = "weights"
                continue

            if line.startswith("- ") and current_section in {"required_sections", "optional_sections"}:
                value = line[2:].strip().strip('"\'')
                if current_section == "required_sections":
                    self.required_sections.append(value)
                else:
                    self.optional_sections.append(value)
                continue

            if current_section == "weights" and ":" in line:
                key, value = line.split(":", 1)
                self.weights[key.strip().strip('"\'')] = float(value.strip())

    def _normalize_sections(self, classifier_output):
        if isinstance(classifier_output, dict):
            if isinstance(classifier_output.get("sections"), list):
                return classifier_output["sections"]
            return []
        if isinstance(classifier_output, list):
            return classifier_output
        return []

    def _expected_items_for_category(self, category):
        return self.section_checklists.get(category, [])

    def _find_evidence(self, content, keywords):
        text = str(content or "")
        lower_text = text.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in lower_text:
                start = max(0, lower_text.find(keyword_lower) - 40)
                end = min(len(text), lower_text.find(keyword_lower) + len(keyword_lower) + 80)
                return text[start:end].strip()
        return ""

    def _looks_like_financial_table(self, content):
        text = str(content or "")
        lower_text = text.lower()

        currency_pattern = r"(?:₹|rs\.?|inr)\s*\d[\d,]*(?:\.\d+)?"
        number_pattern = r"\b\d[\d,]*(?:\.\d+)?\b"

        currency_hits = len(re.findall(currency_pattern, lower_text, flags=re.IGNORECASE))
        number_hits = len(re.findall(number_pattern, lower_text))

        table_keywords = [
            "cost table",
            "capital cost",
            "civil works",
            "plant and machinery",
            "plant equipment",
            "breakup",
            "breakdown",
            "itemized",
            "item-wise",
            "component wise",
            "head wise",
            "contingency",
            "subtotal",
            "total",
            "estimate",
            "line item",
        ]
        keyword_hits = sum(1 for keyword in table_keywords if keyword in lower_text)

        return currency_hits >= 1 and (number_hits >= 4 or keyword_hits >= 2)

    def _evaluate_section(self, section):
        category = str(section.get("category", "")).strip()
        title = str(section.get("title", "")).strip()
        content = str(section.get("content", "")).strip()
        expected_items = list(self._expected_items_for_category(category))

        if category in {"Financial", "Budget"} and self._looks_like_financial_table(content):
            expected_items.append(
                {
                    "item": "Detailed cost table",
                    "weight": 2,
                    "keywords": [
                        "cost table",
                        "breakup",
                        "breakdown",
                        "itemized",
                        "line item",
                        "subtotal",
                        "total",
                        "capital cost",
                        "civil works",
                        "plant equipment",
                    ],
                }
            )

        if not expected_items:
            return {
                "section": title,
                "category": category,
                "score": 0.0,
                "confidence": 0.0,
                "expected_items": [],
                "present": [],
                "missing": [],
                "content": content,
            }

        total_weight = sum(item.get("weight", 1) for item in expected_items)
        present_weight = 0
        present_items = []
        missing_items = []

        for item in expected_items:
            evidence = self._find_evidence(content, item.get("keywords", [item.get("item", "")]))
            if evidence:
                present_items.append(
                    {
                        "item": item["item"],
                        "evidence": evidence,
                        "weight": item.get("weight", 1),
                    }
                )
                present_weight += item.get("weight", 1)
            else:
                missing_items.append(
                    {
                        "item": item["item"],
                        "reason": f"No evidence found for {item['item']}",
                        "weight": item.get("weight", 1),
                    }
                )

        score = 0.0 if total_weight <= 0 else round((present_weight / total_weight) * 100.0, 2)
        confidence = 0.0 if not content else round(min(1.0, len(present_items) / max(1, len(expected_items))), 2)

        return {
            "section": title,
            "category": category,
            "score": score,
            "confidence": confidence,
            "expected_items": [item["item"] for item in expected_items],
            "present": present_items,
            "missing": missing_items,
            "content": content,
        }

    def check_completeness(self, classifier_output):
        sections = self._normalize_sections(classifier_output)
        return {
            "sections": [self._evaluate_section(section) for section in sections if isinstance(section, dict)],
        }

    def _build_validator_payload(self, checklist_result):
        sections = checklist_result.get("sections", [])
        return {
            "input_section_count": len(sections),
            "sections": [
                {
                    "section": section.get("section", ""),
                    "category": section.get("category", ""),
                    "score": section.get("score", 0.0),
                    "confidence": section.get("confidence", 0.0),
                    "expected_items": section.get("expected_items", []),
                    "present": section.get("present", []),
                    "missing": section.get("missing", []),
                    "content": section.get("content", ""),
                }
                for section in sections
            ],
            "summary": {
                "overall_score": self._overall_score(sections),
                "average_score": self._overall_score(sections),
                "weakest_sections": [section.get("section", "") for section in sorted(sections, key=lambda item: item.get("score", 0.0))[:3]],
                "present_sections": [section.get("section", "") for section in sections if section.get("score", 0.0) > 0],
                "missing_sections": [section.get("section", "") for section in sections if section.get("score", 0.0) == 0],
            },
        }

    def _overall_score(self, sections):
        if not sections:
            return 0.0
        return round(sum(section.get("score", 0.0) for section in sections) / len(sections), 2)

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
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass

        return {"sections": [], "summary": {}}

    def _build_fallback_report(self, checklist_result):
        sections = checklist_result.get("sections", [])
        return {
            "sections": sections,
            "summary": {
                "overall_score": self._overall_score(sections),
                "average_score": self._overall_score(sections),
                "weakest_sections": [section.get("section", "") for section in sorted(sections, key=lambda item: item.get("score", 0.0))[:3]],
                "present_sections": [section.get("section", "") for section in sections if section.get("score", 0.0) > 0],
                "missing_sections": [section.get("section", "") for section in sections if section.get("score", 0.0) == 0],
            },
        }

    def validate_with_llm(self, checklist_result):
        payload = self._build_validator_payload(checklist_result)
        query = f"Validate the following deterministic completeness result and return only valid JSON.\n\n{json.dumps(payload, ensure_ascii=False)}"
        response = asyncio.run(self.validator_runner.run_debug(query))
        raw_text = response[-1].content.parts[0].text
        parsed = self._parse_agent_response(raw_text)
        if not parsed.get("sections"):
            return self._build_fallback_report(checklist_result)
        return parsed
    
    def final_chat(self,pdf_path):
        section_classifier = SectionClassifier()
        classified_output = section_classifier.final_json(pdf_path)
        deterministic_result = self.check_completeness(classified_output)
        return self.validate_with_llm(deterministic_result)
    
def main():
    checker = CompletenessChecker()
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"

    print("Response from CompletenessChecker:", checker.final_chat(pdf_path))


if __name__ == "__main__":
    main()
