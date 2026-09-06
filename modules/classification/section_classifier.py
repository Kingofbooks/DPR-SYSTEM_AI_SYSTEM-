import os
import sys
from pathlib import Path
import json

APP_DIR = Path(__file__).resolve().parents[2]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv
from config import config
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

from modules.structure.toc_detector import SectionDetector
import asyncio

load_dotenv()

class SectionClassifier:
    
    def __init__(self):
        self.model_name = config.MODEL_NAME
        self.google_api_key = config.GOOGLE_API_KEY
        self.section_detector = SectionDetector()
        self.retry_config = types.HttpRetryOptions(
                attempts=3,
                exp_base=7,
                initial_delay=1,
                http_status_codes=[429, 500, 503, 504]
            )
            
        self.assistant_agent = LlmAgent(
                name="section_classifier",
                model=Gemini(
                    model=self.model_name,
                    retry=self.retry_config
                ),
                description="Acts as a semantic document classification agent. It analyzes extracted DPR sections and maps each section to a standardized business category regardless of the original heading. The agent normalizes varying document structures into a consistent taxonomy while preserving the original section title and content, enabling downstream quality assessment and analysis to operate on a unified document schema.",
                instruction="""
                You are an expert DPR (Detailed Project Report) Semantic Classification AI.

                Your task is to normalize document sections into a standardized set of business categories.

                The input consists of document sections extracted from a DPR. Each section contains:
                - title
                - content

                The section titles may vary significantly between documents while representing the same business concept.

                For example:
                - "Capital Cost"
                - "Financial Estimate"
                - "Project Cost"
                - "Estimated Cost"
                - "Particulars of Plant & Equipment & Their Estimated Cost"

                may all represent the same semantic category.

                Your job is to understand the meaning of each section using BOTH its title and content, then assign the single most appropriate standardized category.

                Available Categories:
                - Introduction
                - Objectives
                - Technical
                - Financial
                - Budget
                - Timeline
                - Risk
                - Environmental
                - Legal
                - Appendix
                - Other

                Classification Rules:

                1. Base your decision primarily on the semantic meaning of the section, not only its title.

                2. Preserve the original title exactly as provided.

                3. Preserve the original content exactly as provided.

                4. Assign only ONE category from the approved category list.

                5. Include a confidence score between 0.0 and 1.0 representing how confident you are in the classification.

                6. If a section does not clearly fit any predefined category, classify it as "Other".

                7. Never invent, summarize, rewrite, or remove content.

                Output Requirements:

                - Return ONLY valid raw JSON.
                - Do NOT use Markdown.
                - Do NOT include explanations or conversational text.
                - Preserve the order of sections exactly as received.

                Output Schema:

                {
                "sections": [
                    {
                    "title": "string",
                    "category": "Introduction | Objectives | Technical | Financial | Budget | Timeline | Risk | Environmental | Legal | Appendix | Other",
                    "confidence": float,
                    "content": "string"
                    }
                ]
                }
                """
            )
            
        print("Agent created successfully!")
            
        self.runner = InMemoryRunner(agent=self.assistant_agent)
        print("Runner created.")
    
    def classify_sections(self, document_structure):
        payload = {
            "metadata": document_structure.get("metadata", {}),
            "sections": [
                {
                    "title": section.get("title", ""),
                    "content": section.get("content", ""),
                    "start_page": section.get("start_page", 0),
                    "end_page": section.get("end_page", 0),
                }
                for section in document_structure.get("sections", [])
            ],
        }
        query = f"Classify each section into a standard category using both title and content. Return only valid JSON.\n\n{json.dumps(payload, ensure_ascii=False)}"
        response = asyncio.run(self.runner.run_debug(query))
        raw_text = response[-1].content.parts[0].text
        return self._parse_agent_response(raw_text)

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

        return {"sections": []}

    def final_json(self, pdf_path):
        data = self.section_detector.final_section_output(pdf_path)
        return self.classify_sections(data)
        
def main():
    agent = SectionClassifier()
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    print("Response from Agent:", agent.final_json(pdf_path))

if __name__ == "__main__":
    main()