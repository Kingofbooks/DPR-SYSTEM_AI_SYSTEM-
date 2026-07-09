import os
import sys
from pathlib import Path
import json
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
from pdf_reader import PDFReader
from document_schema import DocumentStructure, Section
import asyncio

load_dotenv()

class SectionDetector:
    
    def __init__(self):
        self.model_name = config.MODEL_NAME
        self.google_api_key = config.GOOGLE_API_KEY
        self.pdfreader=PDFReader()
        self.toc_structure_parser_agent= LlmAgent(
                name="toc_structure_parser",
                model=Gemini(
                    model=self.model_name,
                    retry=types.HttpRetryOptions(
                        attempts=3,
                        exp_base=7,
                        initial_delay=1,
                        http_status_codes=[429, 500, 503, 504]
                    ),
                ),
                description="Acts as a structural document analysis agent. It takes raw text blocks from a Table of Contents (TOC) page and parses the structural text hierarchy into a clean array of sections containing exact start and end page boundaries.",                
                instruction="""
                You are an expert Document Layout and Structure Analyzer. Your sole task is to parse a raw string representing a Table of Contents (TOC) page into a clean, structured JSON format.

                Operational Rules:
                1. Analyze the names of the chapters/sections and map out their numerical page ranges.
                2. Infer the end_page for a section by looking at when the next section begins (e.g., If Section 1 starts on page 1, and Section 2 starts on page 4, then Section 1 ends on page 3).
                3. If a section is the last item listed in the table and only has a start page, set its end_page to that same page number.
                4. Keep the exact section title names as they appear in the text string (do not rewrite them).

                Output Format Requirements:
                - You must return a raw JSON object matching the target schema structure exactly.
                - Do not include markdown wraps (like ```json or ```).
                - Do not include any conversational intro, outro, code blocks, or textual explanations.

                Target Schema:
                {
                "sections": [
                    {
                    "title": "string",
                    "start_page": int,
                    "end_page": int
                    }
                ]
                }
                """
            )
            
        print("Agent created successfully!")

    def call_llm_for_structure(self,json):
        page_text=json['page_text']
        for pg_num in sorted(page_text.keys())[:5]:
            page_content = page_text[pg_num].lower()
            if "table of contents" in page_content or "contents" in page_content or "content" in page_content:
                print(f"-> Found Table of Contents on Page {pg_num}")
                return page_content
        return None
    
    def toc_json(self,page_content):
        self.runner = InMemoryRunner(agent=self.toc_structure_parser_agent)
        print("Runner created.")
        query = f"Parse this Table of Contents into structured JSON.\n\nRaw TOC Text:\n{page_content}"
        response= asyncio.run(self.runner.run_debug(query))
        return response[-1].content.parts[0].text
    
    def classify_json(self, contents, json_data):
        cleaned_text = contents.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        cleaned_text = cleaned_text.strip()

        page_text = json_data.get("page_text", {})
        offset = self.get_page_offset(page_text)
        metadata = {
            "filename": json_data.get("filename", ""),
            "resolved_path": json_data.get("resolved_path", ""),
            "num_pages": json_data.get("num_pages", len(page_text)),
        }

        try:
            parsed_sections = json.loads(cleaned_text)
            sec = parsed_sections.get("sections", [])
            sections = []

            for content in sec:
                title = content.get("title", "")
                start_page = int(content.get("start_page", 0))
                end_page = int(content.get("end_page", 0))

                section_text = "\n\n".join(
                    text
                    for page_no, text in page_text.items()
                    if start_page + offset <= int(page_no) <= end_page + offset
                )

                sections.append(
                    Section(
                        title=title,
                        start_page=start_page,
                        end_page=end_page,
                        content=section_text,
                    )
                )

            return DocumentStructure(metadata=metadata, sections=sections).to_dict()

        except json.JSONDecodeError:
            start = cleaned_text.find("{")
            end = cleaned_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned_text[start:end + 1])
            raise
    
    def get_page_offset(self, page_text):
        for pdf_page, text in page_text.items():
            text = text.lower()

            if "chapter-1" in text and "introduction" in text:
                return pdf_page - 1

        return 0
     
    def backup_toc_agent(self, query):
        backup_agent= LlmAgent(
                name="section_detector",
                model=Gemini(
                    model=self.model_name,
                    retry=types.HttpRetryOptions(
                        attempts=3,
                        exp_base=7,
                        initial_delay=1,
                        http_status_codes=[429, 500, 503, 504]
                    ),
                ),
                description="Acts as the backup llm agent that helps extract contents from a given pdf data.Establishes the foundational scope, core background parameters, and primary technical motivations behind the system or project architecture. It anchors the document by detailing the current operational challenges, systemic limitations, and the specific problems this framework intends to address.",
                instruction="""
                You are an expert Document Analysis AI. Your task is to analyze the provided PDF document text structure and build a semantic Table of Contents map.

                Carefully read the text snippets provided for each page number. Identify the starting page for major document sections, specifically: "Introduction", "Objectives", "Budget", and "Timeline". 

                For each section identified:
                1. Extract the full text content belonging to that section.
                2. Record the exact starting page number where that section's header resides.

                You must return a raw JSON object matching this schema precisely. Do not include markdown blocks, conversational text, or explanations.

                Target Schema:
                {
                    "Introduction": { "content": "string", "page": int },
                    "Objectives": { "content": "string", "page": int },
                    "Budget": { "content": "string", "page": int },
                    "Timeline": { "content": "string", "page": int }
                }

                """
            )
            
        print("Agent created successfully!")
            
        runner = InMemoryRunner(agent=backup_agent)
        print("Runner created.")
        response= asyncio.run(runner.run_debug(query))
        return response[-1].content.parts[0].text

    def final_section_output(self, pdf_path):
        json_text = self.pdfreader.get_pdf_data(str(pdf_path))
        page_content = self.call_llm_for_structure(json_text)
        contents = self.toc_json(page_content)
        return self.classify_json(contents, json_text)

def main():
    agent = SectionDetector()
    pdf_path = APP_DIR / "data" / "raw" / "DPR_SAMPLE.pdf"
    if not pdf_path.exists():
        pdf_path = APP_DIR / "data" / "raw" / "sample_dpr.pdf"
    print(agent.final_section_output(pdf_path))

if __name__ == "__main__":
    main()