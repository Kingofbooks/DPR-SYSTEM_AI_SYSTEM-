import re
from difflib import SequenceMatcher


class SectionMapper:

    def __init__(self):
        print("Section Mapper initialized.")

    # =========================================================
    # NORMALIZATION
    # =========================================================

    def normalize_text(self, text: str) -> str:

        if not text:
            return ""

        text = text.lower()

        # Normalize OCR / punctuation variations
        text = text.replace("–", "-")
        text = text.replace("—", "-")

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        text = re.sub(
            r"[^a-z0-9.\s()\-]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def normalize_section_id(self, section_id: str) -> str:

        if not section_id:
            return ""

        section_id = section_id.lower().strip()

        # Normalize common OCR formatting
        section_id = section_id.replace(" ", "")
        section_id = section_id.replace("-", ".")

        return section_id


    # =========================================================
    # TITLE MATCHING
    # =========================================================

    def calculate_similarity(
        self,
        title: str,
        page_text: str
    ) -> float:

        normalized_title = self.normalize_text(title)
        normalized_page = self.normalize_text(page_text)

        if not normalized_title:
            return 0.0

        if not normalized_page:
            return 0.0

        # -----------------------------------------------------
        # Strongest case: exact normalized title exists
        # -----------------------------------------------------

        if normalized_title in normalized_page:
            return 1.0

        title_words = [
            word
            for word in normalized_title.split()
            if len(word) > 2
        ]

        if not title_words:
            return 0.0

        # -----------------------------------------------------
        # Word overlap
        # -----------------------------------------------------

        matched_words = sum(
            1
            for word in title_words
            if word in normalized_page
        )

        word_score = (
            matched_words
            / len(title_words)
        )

        # -----------------------------------------------------
        # Local fuzzy comparison
        # -----------------------------------------------------

        page_words = normalized_page.split()

        original_title_words = (
            normalized_title.split()
        )

        window_size = max(
            len(original_title_words) + 5,
            10
        )

        best_similarity = 0.0

        for i in range(
            0,
            max(
                1,
                len(page_words) - window_size + 1
            )
        ):

            chunk = " ".join(
                page_words[
                    i:
                    i + window_size
                ]
            )

            similarity = SequenceMatcher(
                None,
                normalized_title,
                chunk,
                autojunk=False
            ).ratio()

            best_similarity = max(
                best_similarity,
                similarity
            )

        final_score = (
            0.70 * word_score
            +
            0.30 * best_similarity
        )

        return round(final_score, 3)


    # =========================================================
    # SECTION-ID MATCHING
    # =========================================================

    def section_id_score(
        self,
        section_id: str,
        page_text: str
    ) -> float:

        """
        Look for the section ID in a more controlled way.

        We prefer IDs occurring near the beginning of lines,
        because section headings normally appear there.
        """

        if not section_id or not page_text:
            return 0.0

        normalized_id = (
            self.normalize_section_id(section_id)
        )

        if not normalized_id:
            return 0.0

        lines = page_text.splitlines()

        # -----------------------------------------------------
        # Strong match:
        # section ID occurs near beginning of a line
        # -----------------------------------------------------

        for line in lines:

            normalized_line = (
                self.normalize_text(line)
            )

            compact_line = (
                normalized_line
                .replace(" ", "")
                .replace("-", ".")
            )

            if not compact_line:
                continue

            # Heading IDs usually occur at beginning
            if compact_line.startswith(
                normalized_id
            ):
                return 1.0

        # -----------------------------------------------------
        # Weaker match:
        # ID appears elsewhere on page
        # -----------------------------------------------------

        normalized_page = (
            self.normalize_text(page_text)
        )

        compact_page = (
            normalized_page
            .replace(" ", "")
            .replace("-", ".")
        )

        if normalized_id in compact_page:
            return 0.45

        return 0.0


    # =========================================================
    # PAGE SCORING
    # =========================================================

    def score_page(
        self,
        section: dict,
        text: str
    ) -> float:

        section_id = section.get(
            "section_id",
            ""
        )

        title = section.get(
            "title",
            ""
        )

        id_score = self.section_id_score(
            section_id,
            text
        )

        title_score = self.calculate_similarity(
            title,
            text
        )

        # -----------------------------------------------------
        # Combine evidence
        # -----------------------------------------------------

        if id_score >= 1.0:

            # Strong heading-style ID match
            final_score = (
                0.55
                +
                0.45 * title_score
            )

        elif id_score > 0:

            # ID exists somewhere, but may just be a reference
            final_score = (
                0.20 * id_score
                +
                0.80 * title_score
            )

        else:

            final_score = title_score

        return round(
            min(final_score, 1.0),
            3
        )


    # =========================================================
    # FIND BEST PAGE
    # =========================================================

    def find_best_page(
        self,
        section: dict,
        page_text: dict,
        start_page: int = 0,
        threshold: float = 0.45
    ) -> dict:

        """
        Search only FORWARD from start_page.

        This is the important architectural change.
        """

        best_page = None
        best_score = 0.0

        candidate_scores = []

        sorted_pages = sorted(
            page_text.keys()
        )

        for page_number in sorted_pages:

            # Never search backwards
            if page_number < start_page:
                continue

            text = page_text.get(
                page_number,
                ""
            )

            if not text.strip():
                continue

            score = self.score_page(
                section,
                text
            )

            candidate_scores.append(
                (page_number, score)
            )

            if score > best_score:

                best_score = score
                best_page = page_number

        if (
            best_page is not None
            and best_score >= threshold
        ):

            return {
                "pdf_page": best_page,
                "confidence": round(
                    best_score,
                    3
                ),
                "candidate_scores":
                    candidate_scores
            }

        return {
            "pdf_page": None,
            "confidence": round(
                best_score,
                3
            ),
            "candidate_scores":
                candidate_scores
        }


    # =========================================================
    # MAP SECTIONS
    # =========================================================

    def map_sections(
        self,
        parsed_toc: dict,
        pdf_data: dict,
        toc_result: dict = None,
        threshold: float = 0.45
    ) -> dict:

        print(
            "\nMapping sections progressively..."
        )

        sections = parsed_toc.get(
            "sections",
            []
        )

        page_text = pdf_data.get(
            "page_text",
            {}
        )

        if not sections:

            print(
                "No sections found in parsed TOC."
            )

            return {
                "sections": []
            }

        # =====================================================
        # Find first searchable page
        # =====================================================

        search_start_page = 0

        if toc_result:

            toc_pages = toc_result.get(
                "toc_pages",
                []
            )

            if toc_pages:

                search_start_page = (
                    max(toc_pages) + 1
                )

        print(
            f"Initial search page: "
            f"{search_start_page + 1}"
        )

        mapped_sections = []

        previous_mapped_page = None

        # =====================================================
        # IMPORTANT:
        # Iterate in TOC order.
        # =====================================================

        for index, section in enumerate(
            sections
        ):

            if not isinstance(
                section,
                dict
            ):
                continue

            section_id = section.get(
                "section_id",
                ""
            )

            title = section.get(
                "title",
                ""
            )

            print(
                f"\nSearching | "
                f"{section_id} | "
                f"{title}"
            )

            print(
                f"Search begins at PDF page "
                f"{search_start_page + 1}"
            )

            result = self.find_best_page(
                section=section,
                page_text=page_text,
                start_page=search_start_page,
                threshold=threshold
            )

            mapped_page = result[
                "pdf_page"
            ]

            mapped_section = {

                "section_id":
                    section_id,

                "title":
                    title,

                "page_reference":
                    section.get(
                        "page_reference"
                    ),

                "pdf_page":
                    mapped_page,

                "confidence":
                    result["confidence"]
            }

            mapped_sections.append(
                mapped_section
            )

            # =================================================
            # FOUND
            # =================================================

            if mapped_page is not None:

                # Defensive check
                if (
                    previous_mapped_page
                    is not None
                    and mapped_page
                    < previous_mapped_page
                ):

                    print(
                        "WARNING: "
                        "Backward mapping detected!"
                    )

                print(
                    f"FOUND | "
                    f"{section_id} | "
                    f"{title} | "
                    f"PDF Page "
                    f"{mapped_page + 1} | "
                    f"Confidence: "
                    f"{result['confidence']}"
                )

                previous_mapped_page = (
                    mapped_page
                )

                # ---------------------------------------------
                # IMPORTANT:
                #
                # Start next search from SAME page.
                #
                # Multiple sections can exist on one page.
                # ---------------------------------------------

                search_start_page = (
                    mapped_page
                )

            # =================================================
            # NOT FOUND
            # =================================================

            else:

                print(
                    f"NOT FOUND | "
                    f"{section_id} | "
                    f"{title} | "
                    f"Best Confidence: "
                    f"{result['confidence']}"
                )

                # DO NOT advance search_start_page.
                #
                # If OCR failed for one section,
                # the next section should still be able
                # to search from the last known position.

        # =====================================================
        # VALIDATION
        # =====================================================

        print(
            "\n"
            + "=" * 70
        )

        print(
            "SECTION ORDER VALIDATION"
        )

        print(
            "=" * 70
        )

        last_page = None

        mapped_count = 0

        for section in mapped_sections:

            page = section.get(
                "pdf_page"
            )

            if page is None:

                status = "NOT FOUND"

                display_page = "-"

            else:

                mapped_count += 1

                display_page = page + 1

                if (
                    last_page is not None
                    and page < last_page
                ):

                    status = (
                        "INVALID ORDER"
                    )

                else:

                    status = "OK"

                last_page = page

            print(
                f"{section['section_id']:<12} "
                f"| Page "
                f"{str(display_page):<4} "
                f"| Confidence "
                f"{section['confidence']:<5} "
                f"| {status}"
            )

        print(
            "\nMapped Sections:",
            mapped_count,
            "/",
            len(mapped_sections)
        )

        return {
            "sections":
                mapped_sections
        }

# =========================================
# TEST PIPELINE
# =========================================

def main():

    from pathlib import Path

    from modules.document.pdf_reader import (
        PDFReader
    )

    from modules.structure.toc_detector import (
        TOCDetector
    )

    from modules.structure.toc_parser import (
        TOCParser
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


    # -----------------------------------------
    # 1. READ PDF
    # -----------------------------------------

    print("\n" + "=" * 70)
    print("1. READING PDF")
    print("=" * 70)

    reader = PDFReader()

    pdf_data = reader.get_pdf_data(
        pdf_path
    )


    # -----------------------------------------
    # 2. DETECT TOC
    # -----------------------------------------

    print("\n" + "=" * 70)
    print("2. DETECTING TOC")
    print("=" * 70)

    detector = TOCDetector()

    toc_result = detector.detect(
        pdf_data
    )

    print(
        "TOC Found:",
        toc_result["toc_found"]
    )

    print(
        "TOC Pages:",
        toc_result["toc_pages"]
    )


    # -----------------------------------------
    # 3. PARSE TOC
    # -----------------------------------------

    print("\n" + "=" * 70)
    print("3. PARSING TOC")
    print("=" * 70)

    parser = TOCParser()

    parsed_toc = parser.parse(
        toc_result
    )

    print(
        "Sections Found:",
        len(
            parsed_toc["sections"]
        )
    )

    print("\nTOC SECTIONS:")

    for section in parsed_toc["sections"]:

        print(
            f"  {section.get('section_id')} "
            f"| "
            f"{section.get('title')} "
            f"| "
            f"TOC Page: "
            f"{section.get('page_reference')}"
        )


    # -----------------------------------------
    # 4. MAP SECTIONS
    # -----------------------------------------

    print("\n" + "=" * 70)
    print("4. MAPPING SECTIONS")
    print("=" * 70)

    mapper = SectionMapper()

    result = mapper.map_sections(
        parsed_toc=parsed_toc,
        pdf_data=pdf_data,
        toc_result=toc_result
    )


    # -----------------------------------------
    # 5. FINAL RESULT
    # -----------------------------------------

    print("\n" + "=" * 70)
    print("FINAL SECTION MAPPING")
    print("=" * 70)

    sections = result["sections"]

    for section in sections:

        page_display = (
            str(section['pdf_page'] + 1)
            if section['pdf_page'] is not None
            else 'NOT FOUND'
        )
        print(
            f"{section['section_id']:<12} | "
            f"{section['title']:<45} | "
            f"PDF Page: {page_display:<10} | "
            f"Confidence: {section['confidence']}"
        )


    # -----------------------------------------
    # 6. SUMMARY
    # -----------------------------------------

    found = [
        section
        for section in sections
        if section["pdf_page"] is not None
    ]

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Total TOC sections : {len(sections)}"
    )

    print(
        f"Successfully mapped: {len(found)}"
    )

    print(
        f"Not found          : "
        f"{len(sections) - len(found)}"
    )


# =========================================
# ENTRY POINT
# =========================================

if __name__ == "__main__":
    main()