import re
from pathlib import Path


class SectionExtractor:

    def __init__(self):

        print("Section Extractor initialized.")


    def normalize_text(self, text: str) -> str:

        """
        Normalize text for comparison.

        This helps handle:

        - Upper/lower case differences
        - Extra spaces
        - OCR formatting differences
        """

        text = text.lower()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def find_heading_position(
        self,
        text: str,
        section_id: str,
        title: str
    ):

        """
        Try to find where a section begins
        inside page text.

        Returns:

            character position

        or:

            None
        """

        normalized_text = self.normalize_text(
            text
        )

        normalized_id = self.normalize_text(
            section_id
        )

        normalized_title = self.normalize_text(
            title
        )

        # First try:
        # Find section ID

        if normalized_id:

            position = normalized_text.find(
                normalized_id
            )

            if position != -1:

                return position


        # Second try:
        # Find title

        if normalized_title:

            position = normalized_text.find(
                normalized_title
            )

            if position != -1:

                return position


        return None


    def clean_section_content(
        self,
        content: str
    ) -> str:

        """
        Basic cleanup for extracted
        section content.
        """

        content = re.sub(
            r"\n{3,}",
            "\n\n",
            content
        )

        return content.strip()


    def extract_sections(
        self,
        pdf_data: dict,
        mapped_sections: list
    ) -> list:

        """
        Extract content for every mapped section.

        Parameters:

            pdf_data:
                Output from PDFReader

            mapped_sections:
                Output from SectionMapper

        Returns:

            List of structured sections
        """

        page_text = pdf_data.get(
            "page_text",
            {}
        )


        # Keep only sections that
        # successfully mapped to a PDF page.

        valid_sections = []

        for section in mapped_sections:

            pdf_page = section.get(
                "pdf_page"
            )

            if pdf_page is not None:

                valid_sections.append(
                    section
                )


        # Sort sections by PDF page.

        valid_sections.sort(
            key=lambda section:
                section["pdf_page"]
        )


        extracted_sections = []


        print(
            "\nExtracting section content..."
        )


        for index, section in enumerate(
            valid_sections
        ):


            section_id = section.get(
                "section_id",
                ""
            )

            title = section.get(
                "title",
                ""
            )

            start_page = section.get(
                "pdf_page"
            )


            # Determine the next section.

            next_section = None

            if (
                index + 1
                < len(valid_sections)
            ):

                next_section = (
                    valid_sections[index + 1]
                )


            # If this is the last section,
            # extract until the end of PDF.

            if next_section:

                next_page = (
                    next_section["pdf_page"]
                )

            else:

                next_page = (
                    len(page_text)
                )


            content_parts = []


            # --------------------------------
            # CASE 1:
            # Next section starts on SAME PAGE
            # --------------------------------

            if (
                next_section
                and start_page == next_page
            ):


                page_content = page_text.get(
                    start_page,
                    ""
                )


                start_position = (
                    self.find_heading_position(
                        page_content,
                        section_id,
                        title
                    )
                )


                end_position = (
                    self.find_heading_position(
                        page_content,
                        next_section.get(
                            "section_id",
                            ""
                        ),
                        next_section.get(
                            "title",
                            ""
                        )
                    )
                )


                if (
                    start_position is not None
                    and end_position is not None
                    and end_position > start_position
                ):

                    content = page_content[
                        start_position:end_position
                    ]

                else:

                    # Fallback:
                    # Keep entire page.

                    content = page_content


                content_parts.append(
                    content
                )


                end_page = start_page


            # --------------------------------
            # CASE 2:
            # Section spans multiple pages
            # --------------------------------

            else:


                for page_number in range(
                    start_page,
                    next_page
                ):


                    page_content = (
                        page_text.get(
                            page_number,
                            ""
                        )
                    )


                    # First page:
                    # Try to start from heading.

                    if (
                        page_number
                        == start_page
                    ):


                        start_position = (
                            self.find_heading_position(
                                page_content,
                                section_id,
                                title
                            )
                        )


                        if (
                            start_position
                            is not None
                        ):

                            page_content = (
                                page_content[
                                    start_position:
                                ]
                            )


                    content_parts.append(
                        page_content
                    )


                end_page = (
                    next_page - 1
                )


            content = "\n".join(
                content_parts
            )


            content = (
                self.clean_section_content(
                    content
                )
            )


            extracted_section = {

                "section_id":
                    section_id,

                "title":
                    title,

                "start_page":
                    start_page,

                "end_page":
                    end_page,

                "confidence":
                    section.get(
                        "confidence",
                        0.0
                    ),

                "content":
                    content

            }


            extracted_sections.append(
                extracted_section
            )


            print(

                f"EXTRACTED | "
                f"{section_id} | "
                f"{title} | "
                f"Pages "
                f"{start_page + 1}"
                f"-"
                f"{end_page + 1} | "
                f"Characters: "
                f"{len(content)}"

            )


        return extracted_sections


# =========================================
# TEST PIPELINE
# =========================================

if __name__ == "__main__":

    from modules.document.pdf_reader import (
        PDFReader
    )

    from modules.structure.toc_detector import (
        TOCDetector
    )

    from modules.structure.toc_parser import (
        TOCParser
    )

    from modules.structure.section_mapper import (
        SectionMapper
    )


    BASE_DIR = (
        Path(__file__)
        .resolve()
        .parents[2]
    )


    pdf_path = (

        BASE_DIR
        / "data"
        / "raw"
        / "dpr-kjuice_copy.pdf"

    )


    # -------------------------------------
    # 1. Read PDF
    # -------------------------------------

    reader = PDFReader()

    pdf_data = (
        reader.get_pdf_data(
            pdf_path
        )
    )


    # -------------------------------------
    # 2. Detect TOC
    # -------------------------------------

    toc_detector = TOCDetector()

    toc_result = (
        toc_detector.detect(
            pdf_data
        )
    )


    print(
        "\n--- TOC DETECTION ---"
    )

    print(
        "TOC Found:",
        toc_result["toc_found"]
    )

    print(
        "TOC Pages:",
        toc_result["toc_pages"]
    )


    # -------------------------------------
    # 3. Parse TOC
    # -------------------------------------

    toc_parser = TOCParser()

    parsed_result = (
        toc_parser.parse(
            toc_result
        )
    )

    print(
        "\n--- PARSED SECTIONS ---"
    )

    print(
        "Sections Found:",
        len(parsed_result["sections"])
    )


    # -------------------------------------
    # 4. Map Sections
    # -------------------------------------

    mapper = SectionMapper()

    mapped_sections = (
        mapper.map_sections(
            parsed_result,
            pdf_data,
            toc_result
        )
    )


    # -------------------------------------
    # 5. Extract Sections
    # -------------------------------------

    extractor = SectionExtractor()

    extracted_sections = (
        extractor.extract_sections(
            pdf_data,
            mapped_sections["sections"]
        )
    )


    # -------------------------------------
    # RESULTS
    # -------------------------------------

    print(
        "\n--- EXTRACTED SECTIONS ---"
    )


    for section in extracted_sections:


        print("\n")

        print(
            "=" * 60
        )

        print(
            "SECTION:",
            section["section_id"]
        )

        print(
            "TITLE:",
            section["title"]
        )

        print(
            "PAGES:",
            f"{section['start_page'] + 1}"
            f"-"
            f"{section['end_page'] + 1}"
        )

        print(
            "CONFIDENCE:",
            section["confidence"]
        )

        print(
            "\nCONTENT PREVIEW:"
        )

        print(
            section["content"][:500]
        )