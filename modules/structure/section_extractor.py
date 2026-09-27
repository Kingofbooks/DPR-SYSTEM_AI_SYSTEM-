import json
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

        The normalized text is NEVER used to slice
        the original document.
        """

        if not text:
            return ""

        text = text.lower()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        text = text.replace("–", "-")
        text = text.replace("—", "-")

        return text.strip()

    # =========================================================
    # GET NUMERIC SECTION NUMBER
    # =========================================================

    def get_section_number(
        self,
        section_id: str
    ):
        """
        Convert:

            E.7  -> 7
            E.10 -> 10
            E.13 -> 13

        Returns None when unavailable.
        """

        if not section_id:
            return None

        match = re.search(
            r"[A-Za-z]+\.(\d+)",
            section_id
        )

        if not match:
            return None

        return int(match.group(1))

    # =========================================================
    # FIND NUMBERED DOCUMENT HEADING
    # =========================================================

    def find_numbered_heading_position(
        self,
        text: str,
        section_id: str
    ):
        """
        Find the actual numbered heading used inside
        the DPR.

        Examples:

            E.7  -> 7 CROSS SECTIONAL ELEMENTS
            E.10 -> 10 PAVEMENT DESIGN

        We deliberately look for uppercase heading-like
        text so that table rows such as:

            10 Right Of Way

        are not treated as document headings.
        """

        if not text or not section_id:
            return None

        section_number = self.get_section_number(
            section_id
        )

        if section_number is None:
            return None

        current_position = 0

        for line in text.splitlines(
            keepends=True
        ):

            original_line = line

            stripped = original_line.strip()

            if not stripped:
                current_position += len(
                    original_line
                )
                continue

            # -------------------------------------------------
            # Example:
            #
            # 7 CROSS SECTIONAL ELEMENTS
            # 10 PAVEMENT DESIGN
            # 11. JUNCTION IMPROVEMENT
            # -------------------------------------------------

            match = re.match(
                r"^(\d{1,3})\s*[\.)]?\s+(.+)$",
                stripped
            )

            if match:

                number = int(
                    match.group(1)
                )

                heading_text = (
                    match.group(2).strip()
                )

                # Only accept the expected section number
                if number == section_number:

                    # Heading should look reasonably like
                    # a document heading.
                    letters = re.sub(
                        r"[^A-Za-z]+",
                        "",
                        heading_text
                    )

                    uppercase_letters = sum(
                        1
                        for char in letters
                        if char.isupper()
                    )

                    if (
                        len(letters) >= 4
                        and uppercase_letters
                        / max(len(letters), 1)
                        >= 0.70
                    ):
                        return current_position

            current_position += len(
                original_line
            )

        return None

    # =========================================================
    # FIND NEXT NUMBERED DOCUMENT HEADING
    # =========================================================

    def find_next_numbered_heading(
        self,
        page_text: dict,
        start_page: int,
        end_page: int,
        current_section_id: str
    ):
        """
        Find the next obvious numbered document heading.

        Example:

            E.10 starts at:

                10 PAVEMENT DESIGN

            We detect:

                11. JUNCTION IMPROVEMENT

            and return its page + character position.

        end_page is EXCLUSIVE.
        """

        current_number = self.get_section_number(
            current_section_id
        )

        if current_number is None:
            return None

        for page_number in range(
            start_page,
            end_page
        ):

            text = page_text.get(
                page_number,
                ""
            )

            if not text:
                continue

            current_position = 0

            for line in text.splitlines(
                keepends=True
            ):

                original_line = line
                stripped = original_line.strip()

                if not stripped:
                    current_position += len(
                        original_line
                    )
                    continue

                match = re.match(
                    r"^(\d{1,3})\s*[\.)]?\s+(.+)$",
                    stripped
                )

                if match:

                    number = int(
                        match.group(1)
                    )

                    heading_text = (
                        match.group(2).strip()
                    )

                    # Must be a later numbered section.
                    if number > current_number:

                        letters = re.sub(
                            r"[^A-Za-z]+",
                            "",
                            heading_text
                        )

                        if letters:

                            uppercase_letters = sum(
                                1
                                for char in letters
                                if char.isupper()
                            )

                            uppercase_ratio = (
                                uppercase_letters
                                / max(
                                    len(letters),
                                    1
                                )
                            )

                            # Uppercase heading heuristic.
                            #
                            # This avoids treating:
                            #
                            # 10 Right Of Way
                            #
                            # as a major section heading.
                            if (
                                len(letters) >= 4
                                and uppercase_ratio >= 0.70
                            ):

                                return {
                                    "page": page_number,
                                    "position": current_position,
                                    "number": number,
                                    "text": heading_text
                                }

                current_position += len(
                    original_line
                )

        return None

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

        Search order:

        1. Exact section ID
        2. Title
        3. Actual numbered document heading
        """

        if not text:
            return None

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

        # =====================================================
        # 3. NUMBERED DOCUMENT HEADING
        # =====================================================

        numbered_position = (
            self.find_numbered_heading_position(
                text,
                section_id
            )
        )

        if numbered_position is not None:
            return numbered_position

        return None

    # =========================================================
    # FIND ALL HEADING POSITIONS
    # =========================================================

    def find_all_heading_positions(
        self,
        text: str,
        section_id: str,
        title: str
    ):
        """
        Find possible positions of the section heading.
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

        # Add numbered heading if it wasn't already found.
        numbered_position = (
            self.find_numbered_heading_position(
                text,
                section_id
            )
        )

        if (
            numbered_position is not None
            and numbered_position not in positions
        ):
            positions.append(
                numbered_position
            )

        return positions

    # =========================================================
    # CLEAN CONTENT
    # =========================================================

    def clean_section_content(
        self,
        content: str
    ):

        if not content:
            return ""

        content = re.sub(
            r"\n{3,}",
            "\n\n",
            content
        )

        content = re.sub(
            r"[ \t]{2,}",
            " ",
            content
        )

        return content.strip()

    # =========================================================
    # MAJOR DOCUMENT HEADING
    # =========================================================

    def is_major_document_heading(
        self,
        text: str
    ):

        if not text:
            return False

        first_part = text[:1000]

        normalized = self.normalize_text(
            first_part
        )

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
        Determine the EXCLUSIVE page boundary.

        Normally we use the next mapped section.

        If the next mapped section is several pages away,
        we additionally look for an obvious numbered heading
        inside the range.

        This fixes cases such as:

            E.10
            10 PAVEMENT DESIGN
            ...
            11. JUNCTION IMPROVEMENT
            ...
            E.13
        """

        start_page = current_section[
            "pdf_page"
        ]

        # -----------------------------------------------------
        # Next mapped section
        # -----------------------------------------------------

        if next_section is not None:

            next_page = next_section.get(
                "pdf_page"
            )

            if next_page is not None:

                return next_page

        # -----------------------------------------------------
        # Last mapped section
        # -----------------------------------------------------

        boundary_page = (
            self.find_document_boundary(
                page_text,
                start_page
            )
        )

        if boundary_page is not None:
            return boundary_page

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
        Extract current section when the next mapped section
        starts on the same page.
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

        if (
            current_start is not None
            and next_start is not None
            and next_start > current_start
        ):

            return page_content[
                current_start:next_start
            ]

        if current_start is not None:

            return page_content[
                current_start:
            ]

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
        Extract section content across multiple pages.

        Also detects an obvious numbered section heading
        inside the range and stops there.
        """

        content_parts = []

        section_id = current_section.get(
            "section_id",
            ""
        )

        title = current_section.get(
            "title",
            ""
        )

        # -----------------------------------------------------
        # Find an internal numbered heading.
        #
        # Example:
        #
        # E.10 starts page 12
        #
        # 10 PAVEMENT DESIGN
        #
        # ...
        #
        # 11. JUNCTION IMPROVEMENT
        #
        # Stop at 11.
        # -----------------------------------------------------

        next_document_heading = (
            self.find_next_numbered_heading(
                page_text,
                start_page,
                end_page,
                section_id
            )
        )

        boundary_page = None
        boundary_position = None

        if next_document_heading is not None:

            boundary_page = (
                next_document_heading["page"]
            )

            boundary_position = (
                next_document_heading["position"]
            )

            print(
                f"BOUNDARY | "
                f"{section_id} -> "
                f"Section "
                f"{next_document_heading['number']} "
                f"on PDF Page "
                f"{boundary_page + 1}"
            )

        # -----------------------------------------------------
        # Process pages
        # -----------------------------------------------------

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
            # First page
            # -------------------------------------------------

            if page_number == start_page:

                start_position = (
                    self.find_heading_position(
                        page_content,
                        section_id,
                        title
                    )
                )

                if start_position is not None:

                    page_content = (
                        page_content[
                            start_position:
                        ]
                    )

            # -------------------------------------------------
            # Internal numbered boundary
            # -------------------------------------------------

            if (
                boundary_page is not None
                and page_number == boundary_page
            ):

                page_content = page_content[
                    :boundary_position
                ]

                content_parts.append(
                    page_content
                )

                break

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

        page_text = pdf_data.get(
            "page_text",
            {}
        )

        if not page_text:

            print(
                "No page text available."
            )

            return []

        valid_sections = [

            section

            for section in mapped_sections

            if section.get(
                "pdf_page"
            ) is not None

        ]

        # -----------------------------------------------------
        # Preserve mapper order.
        # -----------------------------------------------------

        extracted_sections = []

        print(
            "\nExtracting section content..."
        )

        # =====================================================
        # PROCESS SECTIONS
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
            # Next mapped section
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
            # Determine mapped page boundary
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
            # MULTI PAGE
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

                if next_page > start_page:

                    end_page = (
                        next_page - 1
                    )

                else:

                    end_page = start_page

            # -------------------------------------------------
            # Clean content
            # -------------------------------------------------

            content = (
                self.clean_section_content(
                    content
                )
            )

            # -------------------------------------------------
            # Output
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
                f"{start_page + 1}-"
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

    # ---------------------------------------------------------
    # BASE DIRECTORY
    # ---------------------------------------------------------

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

    # =========================================================
    # 1. PDF READER
    # =========================================================

    reader = PDFReader()

    pdf_data = (
        reader.get_pdf_data(
            pdf_path
        )
    )

    # =========================================================
    # 2. TOC DETECTION
    # =========================================================

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

    # =========================================================
    # 3. TOC PARSING
    # =========================================================

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

    # =========================================================
    # 4. SECTION MAPPING
    # =========================================================

    mapper = SectionMapper()

    mapped_result = (
        mapper.map_sections(
            parsed_toc=parsed_result,
            pdf_data=pdf_data,
            toc_result=toc_result
        )
    )

    # =========================================================
    # 5. SECTION EXTRACTION
    # =========================================================

    extractor = SectionExtractor()

    extracted_sections = (
        extractor.extract_sections(
            pdf_data,
            mapped_result["sections"]
        )
    )

    # =========================================================
    # 6. EXTRACTION SUMMARY
    # =========================================================

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

    # =========================================================
    # 7. SAVE PROCESSED DOCUMENT
    # =========================================================

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

            "filename":
                pdf_path.name,

            "source":
                str(pdf_path),

            "total_sections":
                len(extracted_sections)

        },

        "sections":
            extracted_sections
    }

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
        "\n"
        + "=" * 70
    )

    print(
        "DOCUMENT SAVED"
    )

    print(
        "=" * 70
    )

    print(
        f"Output: {output_path}"
    )