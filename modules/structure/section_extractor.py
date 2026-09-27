import re
from pathlib import Path


class SectionExtractor:

    def __init__(self):
        print("Section Extractor initialized.")

    # =========================================================
    # TEXT NORMALIZATION
    # =========================================================

    def normalize_text(self, text: str) -> str:
        """
        Normalize text only for comparison.

        IMPORTANT:
        This normalized text is NEVER used for slicing
        the original document.
        """

        if not text:
            return ""

        text = text.lower()

        # Normalize whitespace
        text = re.sub(
            r"\s+",
            " ",
            text
        )

        # Normalize common OCR punctuation
        text = text.replace(
            "–",
            "-"
        )

        text = text.replace(
            "—",
            "-"
        )

        return text.strip()

    # =========================================================
    # FIND HEADING POSITION
    # =========================================================

    def find_heading_position(
        self,
        text: str,
        section_id: str,
        title: str
    ):
        """
        Find a section heading inside ORIGINAL text.

        Returns a character position belonging to the
        original string.

        We NEVER use a position calculated from a
        normalized copy to slice the original text.
        """

        if not text:
            return None

        normalized_id = self.normalize_text(
            section_id
        )

        normalized_title = self.normalize_text(
            title
        )

        # -----------------------------------------------------
        # Build original-line positions
        # -----------------------------------------------------

        current_position = 0

        for line in text.splitlines(
            keepends=True
        ):

            original_line = line

            normalized_line = (
                self.normalize_text(
                    original_line
                )
            )

            if not normalized_line:
                current_position += len(
                    original_line
                )
                continue

            # =================================================
            # 1. SECTION ID MATCH
            # =================================================

            if normalized_id:

                compact_line = (
                    normalized_line
                    .replace(" ", "")
                )

                compact_id = (
                    normalized_id
                    .replace(" ", "")
                )

                if compact_id in compact_line:

                    return current_position

            # =================================================
            # 2. TITLE MATCH
            # =================================================

            if (
                normalized_title
                and normalized_title
                in normalized_line
            ):

                return current_position

            current_position += len(
                original_line
            )

        return None

    # =========================================================
    # FIND ALL HEADING POSITIONS ON A PAGE
    # =========================================================

    def find_all_heading_positions(
        self,
        text: str,
        section_id: str,
        title: str
    ):
        """
        Find possible heading positions.

        Useful when OCR text contains repeated references
        to the section ID/title.

        Returns a list of original-text positions.
        """

        positions = []

        if not text:
            return positions

        normalized_id = self.normalize_text(
            section_id
        )

        normalized_title = self.normalize_text(
            title
        )

        current_position = 0

        for line in text.splitlines(
            keepends=True
        ):

            original_line = line

            normalized_line = (
                self.normalize_text(
                    original_line
                )
            )

            if normalized_line:

                matched = False

                # ---------------------------------------------
                # Section ID
                # ---------------------------------------------

                if normalized_id:

                    compact_line = (
                        normalized_line
                        .replace(" ", "")
                    )

                    compact_id = (
                        normalized_id
                        .replace(" ", "")
                    )

                    if compact_id in compact_line:
                        matched = True

                # ---------------------------------------------
                # Title
                # ---------------------------------------------

                if (
                    not matched
                    and normalized_title
                    and normalized_title
                    in normalized_line
                ):
                    matched = True

                if matched:

                    positions.append(
                        current_position
                    )

            current_position += len(
                original_line
            )

        return positions

    # =========================================================
    # CLEAN CONTENT
    # =========================================================

    def clean_section_content(
        self,
        content: str
    ) -> str:

        if not content:
            return ""

        # Remove excessive blank lines
        content = re.sub(
            r"\n{3,}",
            "\n\n",
            content
        )

        # Remove excessive spaces
        content = re.sub(
            r"[ \t]{2,}",
            " ",
            content
        )

        return content.strip()

    # =========================================================
    # DOCUMENT BOUNDARY DETECTION
    # =========================================================

    def is_major_document_heading(
        self,
        text: str
    ) -> bool:
        """
        Determine whether the beginning of a page looks
        like a major document/chapter boundary.

        This is deliberately conservative.
        """

        if not text:
            return False

        # Only inspect the beginning of the page.
        first_part = text[:1000]

        normalized = self.normalize_text(
            first_part
        )

        # -----------------------------------------------------
        # CHAPTER 1
        # CHAPTER-I
        # CHAPTER III
        # -----------------------------------------------------

        chapter_patterns = [

            r"^chapter\s*[-:]?\s*[ivxlcdm]+",

            r"^chapter\s*[-:]?\s*\d+",

        ]

        for pattern in chapter_patterns:

            if re.search(
                pattern,
                normalized,
                re.IGNORECASE
            ):

                return True

        return False

    # =========================================================
    # FIND DOCUMENT BOUNDARY
    # =========================================================

    def find_document_boundary(
        self,
        page_text: dict,
        start_page: int
    ):
        """
        Find the first major document boundary after
        start_page.

        Returns the PDF page number where the next major
        document section begins.

        Example:

            E.21 starts page 18
            CHAPTER 1 starts page 19

        returns:

            18  (zero-indexed page 19)
        """

        for page_number in sorted(
            page_text.keys()
        ):

            if page_number <= start_page:
                continue

            text = page_text.get(
                page_number,
                ""
            )

            if not text.strip():
                continue

            if self.is_major_document_heading(
                text
            ):

                return page_number

        return None

    # =========================================================
    # DETERMINE END PAGE
    # =========================================================

    def determine_end_boundary(
        self,
        page_text: dict,
        current_section,
        next_section
    ):
        """
        Determine where the current section ends.

        Returns the EXCLUSIVE end page.

        Example:

            current = page 17
            next = page 20

            return 20

            => pages 17,18,19
        """

        start_page = current_section[
            "pdf_page"
        ]

        # -----------------------------------------------------
        # CASE 1:
        # There is a next mapped section.
        # -----------------------------------------------------

        if next_section is not None:

            next_page = next_section[
                "pdf_page"
            ]

            if next_page is not None:

                return next_page

        # -----------------------------------------------------
        # CASE 2:
        # Last mapped section.
        #
        # DO NOT automatically use len(page_text).
        # -----------------------------------------------------

        boundary_page = (
            self.find_document_boundary(
                page_text,
                start_page
            )
        )

        if boundary_page is not None:

            return boundary_page

        # -----------------------------------------------------
        # CASE 3:
        # No structural boundary found.
        #
        # Conservative fallback:
        # use the end of the PDF.
        # -----------------------------------------------------

        return len(page_text)

    # =========================================================
    # EXTRACT SAME-PAGE SECTION
    # =========================================================

    def extract_same_page_section(
        self,
        page_content: str,
        current_section,
        next_section
    ):
        """
        Extract a section when current and next section
        start on the same PDF page.
        """

        current_start = (
            self.find_heading_position(
                page_content,
                current_section.get(
                    "section_id",
                    ""
                ),
                current_section.get(
                    "title",
                    ""
                )
            )
        )

        next_start = (
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

        # -----------------------------------------------------
        # Ideal case
        # -----------------------------------------------------

        if (
            current_start is not None
            and next_start is not None
            and next_start > current_start
        ):

            return page_content[
                current_start:
                next_start
            ]

        # -----------------------------------------------------
        # If current heading found but next heading isn't,
        # take from current heading to page end.
        # -----------------------------------------------------

        if current_start is not None:

            return page_content[
                current_start:
            ]

        # -----------------------------------------------------
        # Last fallback
        # -----------------------------------------------------

        return page_content

    # =========================================================
    # EXTRACT MULTI-PAGE SECTION
    # =========================================================

    def extract_multi_page_section(
        self,
        page_text: dict,
        start_page: int,
        end_page: int,
        current_section
    ):
        """
        Extract a section spanning multiple pages.

        end_page is EXCLUSIVE.
        """

        content_parts = []

        for page_number in range(
            start_page,
            end_page
        ):

            page_content = page_text.get(
                page_number,
                ""
            )

            if not page_content:
                continue

            # -------------------------------------------------
            # First page:
            # remove material before heading.
            # -------------------------------------------------

            if page_number == start_page:

                start_position = (
                    self.find_heading_position(
                        page_content,
                        current_section.get(
                            "section_id",
                            ""
                        ),
                        current_section.get(
                            "title",
                            ""
                        )
                    )
                )

                if start_position is not None:

                    page_content = (
                        page_content[
                            start_position:
                        ]
                    )

            content_parts.append(
                page_content
            )

        return "\n".join(
            content_parts
        )

    # =========================================================
    # MAIN EXTRACTION
    # =========================================================

    def extract_sections(
        self,
        pdf_data: dict,
        mapped_sections: list
    ) -> list:
        """
        Extract content for every mapped section.

        Handles:

        - same-page sections
        - multi-page sections
        - final-section boundaries
        - original-text heading positions
        """

        page_text = pdf_data.get(
            "page_text",
            {}
        )

        if not page_text:

            print(
                "No page text available."
            )

            return []

        # -----------------------------------------------------
        # Keep only successfully mapped sections
        # -----------------------------------------------------

        valid_sections = [

            section
            for section in mapped_sections

            if (
                section.get(
                    "pdf_page"
                )
                is not None
            )

        ]

        # -----------------------------------------------------
        # Preserve TOC order.
        #
        # The mapper already gives us the correct order.
        # -----------------------------------------------------

        valid_sections.sort(
            key=lambda section:
                section["pdf_page"]
        )

        extracted_sections = []

        print(
            "\nExtracting section content..."
        )

        # =====================================================
        # PROCESS EACH SECTION
        # =====================================================

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

            # -------------------------------------------------
            # Determine next section
            # -------------------------------------------------

            next_section = None

            if (
                index + 1
                < len(valid_sections)
            ):

                next_section = (
                    valid_sections[
                        index + 1
                    ]
                )

            # -------------------------------------------------
            # Determine end boundary
            # -------------------------------------------------

            next_page = (
                self.determine_end_boundary(
                    page_text,
                    section,
                    next_section
                )
            )

            # =================================================
            # SAME PAGE
            # =================================================

            if (
                next_section is not None
                and
                next_section.get(
                    "pdf_page"
                ) == start_page
            ):

                page_content = (
                    page_text.get(
                        start_page,
                        ""
                    )
                )

                content = (
                    self.extract_same_page_section(
                        page_content,
                        section,
                        next_section
                    )
                )

                end_page = start_page

            # =================================================
            # MULTI-PAGE
            # =================================================

            else:

                content = (
                    self.extract_multi_page_section(
                        page_text,
                        start_page,
                        next_page,
                        section
                    )
                )

                # -------------------------------------------------
                # next_page is EXCLUSIVE
                # -------------------------------------------------

                if next_page > start_page:

                    end_page = (
                        next_page - 1
                    )

                else:

                    end_page = start_page

            # -------------------------------------------------
            # Clean
            # -------------------------------------------------

            content = (
                self.clean_section_content(
                    content
                )
            )

            # -------------------------------------------------
            # Build output
            # -------------------------------------------------

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


# =========================================================
# TEST PIPELINE
# =========================================================

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
        / "DPR of Road.pdf"
    )


    # ---------------------------------------------------------
    # 1. PDF READER
    # ---------------------------------------------------------

    reader = PDFReader()

    pdf_data = (
        reader.get_pdf_data(
            pdf_path
        )
    )


    # ---------------------------------------------------------
    # 2. TOC DETECTION
    # ---------------------------------------------------------

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


    # ---------------------------------------------------------
    # 3. TOC PARSING
    # ---------------------------------------------------------

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
        len(
            parsed_result["sections"]
        )
    )


    # ---------------------------------------------------------
    # 4. SECTION MAPPING
    # ---------------------------------------------------------

    mapper = SectionMapper()

    mapped_result = (
        mapper.map_sections(
            parsed_toc=parsed_result,
            pdf_data=pdf_data,
            toc_result=toc_result
        )
    )


    # ---------------------------------------------------------
    # 5. SECTION EXTRACTION
    # ---------------------------------------------------------

    extractor = SectionExtractor()

    extracted_sections = (
        extractor.extract_sections(
            pdf_data,
            mapped_result["sections"]
        )
    )


    # ---------------------------------------------------------
    # 6. RESULTS
    # ---------------------------------------------------------

    print(
        "\n"
        + "=" * 70
    )

    print(
        "EXTRACTION SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"Mapped sections: "
        f"{len(mapped_result['sections'])}"
    )

    print(
        f"Extracted sections: "
        f"{len(extracted_sections)}"
    )

    print()

    for section in extracted_sections:

        print(
            f"{section['section_id']:<10} | "
            f"{section['title']:<45} | "
            f"Pages "
            f"{section['start_page'] + 1}-"
            f"{section['end_page'] + 1} | "
            f"Chars "
            f"{len(section['content'])}"
        )
        # ---------------------------------------------------------
    # 7. SAVE EXTRACTED DOCUMENT
    # ---------------------------------------------------------

    output_path = (
        BASE_DIR
        / "data"
        / "processed"
        / "DPR of Road.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    document = {
        "metadata": {
            "filename": pdf_path.name,
            "source": str(pdf_path),
            "total_sections": len(extracted_sections),
        },
        "sections": extracted_sections,
    }

    import json

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

    print()
    print("=" * 70)
    print("DOCUMENT SAVED")
    print("=" * 70)
    print(f"Output: {output_path}")