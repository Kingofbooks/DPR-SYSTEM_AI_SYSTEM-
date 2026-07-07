import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv
from config import config
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.tools import google_search
from google.adk.runners import InMemoryRunner
from google.genai import types

from section_detector import SectionDetector
import asyncio

load_dotenv()

class SectionClassifier:
    
    def __init__(self):
        self.model_name = config.MODEL_NAME
        self.google_api_key = config.GOOGLE_API_KEY
        self.section_dector=SectionDetector()
        self.retry_config=types.HttpRetryOptions(
                attempts=3,
                exp_base=7,
                initial_delay=1,
                http_status_codes=[429, 500, 503, 504]
            )
            
        self.assistant_agent= LlmAgent(
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
    
    def chat_section_classifier(self, query):
        self.response= asyncio.run(self.runner.run_debug(query))
        return self.response[-1].content.parts[0].text

def main():
    agent = SectionClassifier()
    section_deductor=SectionDetector()
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    data=section_deductor.final_section_output(pdf_path)
    chat1=agent.chat_section_classifier(data)
    print("Response from Agent:", chat1)

if __name__ == "__main__":
    main()