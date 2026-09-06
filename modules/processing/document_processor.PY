import json
import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# IMPORT PIPELINE MODULES
# ============================================================

from modules.document.pdf_reader import PDFReader

from modules.structure.toc_detector import TOCDetector

from modules.structure.toc_parser import TOCParser

from modules.structure.section_mapper import SectionMapper

from modules.structure.section_extractor import SectionExtractor


# ============================================================
# DOCUMENT PROCESSOR
# ============================================================

class DocumentProcessor:
    """
    Central DPR document processing pipeline.

    Pipeline:

        PDF
         |
         v
        PDFReader
         |
         v
        TOCDetector
         |
         v
        TOCParser
         |
         v
        SectionMapper
         |
         v
        SectionExtractor
         |
         v
        Structured Document
    """


    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        print("\n" + "=" * 60)
        print("DOCUMENT PROCESSOR INITIALIZED")
        print("=" * 60)


        # ----------------------------------------------------
        # Initialize PDF Reader
        # ----------------------------------------------------

        self.pdf_reader = PDFReader()


        # ----------------------------------------------------
        # Initialize TOC Detector
        # ----------------------------------------------------

        self.toc_detector = TOCDetector()


        # ----------------------------------------------------
        # Initialize TOC Parser
        # ----------------------------------------------------

        self.toc_parser = TOCParser()


        # ----------------------------------------------------
        # Initialize Section Mapper
        # ----------------------------------------------------

        self.section_mapper = SectionMapper()


        # ----------------------------------------------------
        # Initialize Section Extractor
        # ----------------------------------------------------

        self.section_extractor = SectionExtractor()


    # ========================================================
    # PROCESS DOCUMENT
    # ========================================================

    def process(
        self,
        pdf_path
    ) -> dict:

        # ----------------------------------------------------
        # Convert to Path
        # ----------------------------------------------------

        pdf_path = Path(pdf_path)


        # ----------------------------------------------------
        # Check PDF exists
        # ----------------------------------------------------

        if not pdf_path.exists():

            raise FileNotFoundError(

                f"\nPDF file not found:\n"
                f"{pdf_path}"

            )


        # ====================================================
        # START PIPELINE
        # ====================================================

        print("\n")
        print("=" * 60)

        print("STARTING DOCUMENT PROCESSING")

        print("=" * 60)

        print(

            f"\nPDF: "
            f"{pdf_path.name}"

        )


        # ====================================================
        # STEP 1
        # READ PDF
        # ====================================================

        print("\n")

        print("-" * 60)

        print("STEP 1: READING PDF")

        print("-" * 60)


        pdf_data = (

            self.pdf_reader.get_pdf_data(

                pdf_path

            )

        )


        # ----------------------------------------------------
        # Get PDF information
        # ----------------------------------------------------

        filename = pdf_data.get(

            "filename",

            pdf_path.name

        )


        num_pages = pdf_data.get(

            "num_pages",

            0

        )


        print(

            f"\nPDF successfully read."

        )


        print(

            f"Filename: "
            f"{filename}"

        )


        print(

            f"Total Pages: "
            f"{num_pages}"

        )


        # ====================================================
        # STEP 2
        # DETECT TABLE OF CONTENTS
        # ====================================================

        print("\n")

        print("-" * 60)

        print("STEP 2: DETECTING TABLE OF CONTENTS")

        print("-" * 60)


        toc_result = (

            self.toc_detector.detect(

                pdf_data

            )

        )


        # ----------------------------------------------------
        # Extract TOC information
        # ----------------------------------------------------

        toc_found = toc_result.get(

            "toc_found",

            False

        )


        toc_pages = toc_result.get(

            "toc_pages",

            []

        )


        toc_confidence = toc_result.get(

            "confidence",

            0.0

        )


        toc_text = toc_result.get(

            "toc_text",

            ""

        )


        print(

            f"\nTOC Found: "
            f"{toc_found}"

        )


        print(

            f"TOC Pages: "
            f"{toc_pages}"

        )


        print(

            f"TOC Confidence: "
            f"{toc_confidence}"

        )


        # ====================================================
        # DEFAULT VALUES
        # ====================================================

        parsed_sections = []

        mapped_sections = []

        extracted_sections = []


        # ====================================================
        # STEP 3
        # PARSE TOC
        # ====================================================

        if toc_found and toc_text.strip():

            print("\n")

            print("-" * 60)

            print("STEP 3: PARSING TABLE OF CONTENTS")

            print("-" * 60)


            parsed_result = (

                self.toc_parser.parse(

                    toc_result

                )

            )


            # ------------------------------------------------
            # Extract sections safely
            # ------------------------------------------------

            if isinstance(

                parsed_result,

                dict

            ):

                parsed_sections = (

                    parsed_result.get(

                        "sections",

                        []

                    )

                )


            elif isinstance(

                parsed_result,

                list

            ):

                parsed_sections = (

                    parsed_result

                )


            else:

                print(

                    "\nWARNING: Unexpected "
                    "TOC parser output."

                )

                parsed_sections = []


            print(

                f"\nParsed Sections: "
                f"{len(parsed_sections)}"

            )


        else:

            print("\n")

            print("-" * 60)

            print("STEP 3: SKIPPING TOC PARSING")

            print("-" * 60)

            print(

                "\nNo valid Table of Contents "
                "was detected."

            )


        # ====================================================
        # STEP 4
        # MAP SECTIONS
        # ====================================================

        if parsed_sections:

            print("\n")

            print("-" * 60)

            print("STEP 4: MAPPING SECTIONS")

            print("-" * 60)


            mapped_sections = (

                self.section_mapper.map_sections(

                    parsed_result,

                    pdf_data,

                    toc_result

                )

            )


            # ------------------------------------------------
            # Safety check
            # ------------------------------------------------

            if mapped_sections is None:

                mapped_sections = {

                    "sections": []

                }


            mapped_section_list = mapped_sections.get(

                "sections",

                []

            )


            print(

                f"\nMapped Sections: "
                f"{len(mapped_section_list)}"

            )


        else:

            print("\n")

            print("-" * 60)

            print("STEP 4: SKIPPING SECTION MAPPING")

            print("-" * 60)

            print(

                "\nNo sections available "
                "for mapping."

            )


        # ====================================================
        # STEP 5
        # EXTRACT SECTION CONTENT
        # ====================================================

        if mapped_section_list:

            print("\n")

            print("-" * 60)

            print("STEP 5: EXTRACTING SECTION CONTENT")

            print("-" * 60)


            extracted_sections = (

                self.section_extractor.extract_sections(

                    pdf_data,

                    mapped_section_list

                )

            )


            # ------------------------------------------------
            # Safety check
            # ------------------------------------------------

            if extracted_sections is None:

                extracted_sections = []


            print(

                f"\nExtracted Sections: "
                f"{len(extracted_sections)}"

            )


        else:

            print("\n")

            print("-" * 60)

            print("STEP 5: SKIPPING SECTION EXTRACTION")

            print("-" * 60)

            print(

                "\nNo mapped sections available "
                "for extraction."

            )


        # ====================================================
        # BUILD FINAL DOCUMENT
        # ====================================================

        document = {

            # ------------------------------------------------
            # DOCUMENT INFORMATION
            # ------------------------------------------------

            "metadata": {

                "filename":

                    filename,


                "resolved_path":

                    pdf_data.get(

                        "resolved_path",

                        str(
                            pdf_path.resolve()
                        )

                    ),


                "num_pages":

                    num_pages

            },


            # ------------------------------------------------
            # TOC INFORMATION
            # ------------------------------------------------

            "toc": {

                "found":

                    toc_found,


                "pages":

                    toc_pages,


                "confidence":

                    toc_confidence

            },


            # ------------------------------------------------
            # PARSED STRUCTURE
            # ------------------------------------------------

            "parsed_sections":

                parsed_sections,


            # ------------------------------------------------
            # MAPPED STRUCTURE
            # ------------------------------------------------

            "mapped_sections":

                mapped_sections,


            # ------------------------------------------------
            # EXTRACTED CONTENT
            # ------------------------------------------------

            "sections":

                extracted_sections

        }


        # ====================================================
        # PIPELINE COMPLETE
        # ====================================================

        print("\n")

        print("=" * 60)

        print("DOCUMENT PROCESSING COMPLETE")

        print("=" * 60)


        print(

            f"\nDocument: "
            f"{filename}"

        )


        print(

            f"Pages: "
            f"{num_pages}"

        )


        print(

            f"TOC Found: "
            f"{toc_found}"

        )


        print(

            f"Parsed Sections: "
            f"{len(parsed_sections)}"

        )


        print(

            f"Mapped Sections: "
            f"{len(mapped_sections)}"

        )


        print(

            f"Extracted Sections: "
            f"{len(extracted_sections)}"

        )


        return document


    # ========================================================
    # SAVE DOCUMENT
    # ========================================================

    def save_json(
        self,
        document: dict,
        output_path
    ) -> Path:

        output_path = Path(

            output_path

        )


        # ----------------------------------------------------
        # Create parent directories
        # ----------------------------------------------------

        output_path.parent.mkdir(

            parents=True,

            exist_ok=True

        )


        # ----------------------------------------------------
        # Save JSON
        # ----------------------------------------------------

        with open(

            output_path,

            "w",

            encoding="utf-8"

        ) as file:

            json.dump(

                document,

                file,

                indent=4,

                ensure_ascii=False

            )


        print(

            f"\nDocument saved successfully:"

        )

        print(

            output_path.resolve()

        )


        return output_path


# ============================================================
# MAIN
# ============================================================

def main():


    # ========================================================
    # PROJECT ROOT
    # ========================================================

    BASE_DIR = (

        Path(__file__)
        .resolve()
        .parents[2]

    )


    # ========================================================
    # INPUT PDF
    # ========================================================

    pdf_path = (

        BASE_DIR

        / "data"

        / "raw"

        / "DPR of Road.pdf"

    )


    # ========================================================
    # FALLBACK PDF
    # ========================================================

    if not pdf_path.exists():

        pdf_path = (

            BASE_DIR

            / "data"

            / "raw"

            / "model_dpr.pdf"

        )


    # ========================================================
    # CHECK FILE
    # ========================================================

    if not pdf_path.exists():

        raise FileNotFoundError(

            "\nCould not find a PDF file.\n\n"

            "Checked:\n"

            f"{BASE_DIR / 'data' / 'raw' / 'DPR of Road.pdf'}\n"

            "and\n"

            f"{BASE_DIR / 'data' / 'raw' / 'model_dpr.pdf'}"

        )


    # ========================================================
    # CREATE PROCESSOR
    # ========================================================

    processor = (

        DocumentProcessor()

    )


    # ========================================================
    # PROCESS PDF
    # ========================================================

    document = (

        processor.process(

            pdf_path

        )

    )


    # ========================================================
    # OUTPUT PATH
    # ========================================================

    output_path = (

        BASE_DIR

        / "data"

        / "processed"

        / f"{pdf_path.stem}.json"

    )


    # ========================================================
    # SAVE RESULT
    # ========================================================

    processor.save_json(

        document,

        output_path

    )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")

    print("=" * 60)

    print("FINAL RESULT")

    print("=" * 60)


    metadata = document.get(

        "metadata",

        {}

    )


    toc = document.get(

        "toc",

        {}

    )


    sections = document.get(

        "sections",

        []

    )


    print(

        f"\nFilename: "
        f"{metadata.get('filename')}"

    )


    print(

        f"Total Pages: "
        f"{metadata.get('num_pages')}"

    )


    print(

        f"TOC Found: "
        f"{toc.get('found')}"

    )


    print(

        f"TOC Pages: "
        f"{toc.get('pages')}"

    )


    print(

        f"Extracted Sections: "
        f"{len(sections)}"

    )


    # ========================================================
    # PRINT SECTIONS
    # ========================================================

    if sections:

        print("\n")

        print("-" * 60)

        print("EXTRACTED SECTIONS")

        print("-" * 60)


        for section in sections:


            section_id = (

                section.get(

                    "section_id",

                    "UNKNOWN"

                )

            )


            title = (

                section.get(

                    "title",

                    "UNKNOWN"

                )

            )


            start_page = (

                section.get(

                    "start_page",

                    None

                )

            )


            end_page = (

                section.get(

                    "end_page",

                    None

                )

            )


            confidence = (

                section.get(

                    "confidence",

                    0.0

                )

            )


            content = (

                section.get(

                    "content",

                    ""

                )

            )


            print("\n")

            print(

                f"SECTION: "
                f"{section_id}"

            )


            print(

                f"TITLE: "
                f"{title}"

            )


            # Page numbers inside your
            # current pipeline are zero-indexed.
            # Convert them only for display.

            if start_page is not None:

                display_start_page = (

                    start_page + 1

                )

            else:

                display_start_page = (

                    "UNKNOWN"

                )


            if end_page is not None:

                display_end_page = (

                    end_page + 1

                )

            else:

                display_end_page = (

                    "UNKNOWN"

                )


            print(

                f"PAGES: "
                f"{display_start_page}"
                f"-"
                f"{display_end_page}"

            )


            print(

                f"CONFIDENCE: "
                f"{confidence}"

            )


            print(

                f"CONTENT LENGTH: "
                f"{len(content)}"

            )


    print("\n")

    print("=" * 60)

    print("DONE")

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()