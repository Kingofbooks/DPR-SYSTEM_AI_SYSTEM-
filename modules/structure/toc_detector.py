import re
from pathlib import Path


class TOCDetector:

    def __init__(self):

        self.toc_keywords = [

            "table of contents",

            "contents",

            "index",

            "list of contents",

            "list of chapters",

            "chapter list"

        ]


    # --------------------------------------------------
    # KEYWORD SCORE
    # --------------------------------------------------

    def keyword_score(
        self,
        text: str
    ) -> float:

        """
        Check for explicit TOC-related keywords.
        """

        text = text.lower()

        for keyword in self.toc_keywords:

            if keyword in text:

                return 0.40

        return 0.0


    # --------------------------------------------------
    # PAGE NUMBER SCORE
    # --------------------------------------------------

    def page_number_score(
        self,
        text: str
    ) -> float:

        """
        TOC pages usually contain many
        page numbers or references.

        Examples:

        1
        12
        25
        ES-1
        CE-4
        """

        # Normal numbers

        normal_numbers = re.findall(

            r"\b\d{1,4}\b",

            text

        )


        # Alphanumeric page labels

        special_pages = re.findall(

            r"\b[A-Za-z]{1,5}-\d+\b",

            text

        )


        total = (

            len(normal_numbers)

            +

            len(special_pages)

        )


        if total >= 10:

            return 0.20


        if total >= 6:

            return 0.15


        if total >= 3:

            return 0.10


        return 0.0


    # --------------------------------------------------
    # PAGE RANGE SCORE
    # --------------------------------------------------

    def page_range_score(
        self,
        text: str
    ) -> float:

        """
        Detect page ranges.

        Examples:

        1-5
        1 – 5
        10 to 20
        CE-1 to CE-50
        """

        patterns = [

            # 1-5

            r"\b\d+\s*[-–]\s*\d+\b",


            # 1 to 5

            r"\b\d+\s+to\s+\d+\b",


            # CE-1 to CE-50

            r"\b[A-Za-z]+-\d+\s+to\s+[A-Za-z]+-\d+\b"

        ]


        matches = []


        for pattern in patterns:

            matches.extend(

                re.findall(

                    pattern,

                    text,

                    flags=re.IGNORECASE

                )

            )


        if len(matches) >= 3:

            return 0.15


        if len(matches) >= 1:

            return 0.10


        return 0.0


    # --------------------------------------------------
    # NUMBERED SECTION SCORE
    # --------------------------------------------------

    def numbered_section_score(
        self,
        text: str
    ) -> float:

        """
        Detect numbered sections.

        Examples:

        1. Introduction

        2. Objectives

        3. Technical Details

        1.1 Project Background

        Chapter 1
        """

        patterns = [

            # 1. Introduction

            r"(?im)^\s*\d+[\.\)]",


            # 1.1 Section

            r"(?im)^\s*\d+\.\d+",


            # Chapter 1

            r"(?im)^\s*chapter\s+\d+"

        ]


        matches = []


        for pattern in patterns:

            matches.extend(

                re.findall(

                    pattern,

                    text,

                    flags=re.IGNORECASE

                )

            )


        if len(matches) >= 6:

            return 0.15


        if len(matches) >= 3:

            return 0.10


        return 0.0


    # --------------------------------------------------
    # CHAPTER SCORE
    # --------------------------------------------------

    def chapter_score(
        self,
        text: str
    ) -> float:

        """
        Check for repeated chapter/section
        terminology.
        """

        matches = re.findall(

            r"(?i)\bchapter\b",

            text

        )


        if len(matches) >= 3:

            return 0.10


        return 0.0


    # --------------------------------------------------
    # DOTTED LEADER SCORE
    # --------------------------------------------------

    def dotted_leader_score(
        self,
        text: str
    ) -> float:

        """
        Many TOCs use dotted leaders.

        Example:

        Introduction ............ 1
        Budget ................. 15
        """

        matches = re.findall(

            r"\.{3,}",

            text

        )


        if len(matches) >= 5:

            return 0.10


        if len(matches) >= 2:

            return 0.05


        return 0.0


    # --------------------------------------------------
    # CALCULATE TOTAL SCORE
    # --------------------------------------------------

    def calculate_score(
        self,
        text: str
    ) -> float:

        """
        Combine all deterministic
        TOC detection signals.
        """

        if not text.strip():

            return 0.0


        score = 0.0


        score += self.keyword_score(text)

        score += self.page_number_score(text)

        score += self.page_range_score(text)

        score += self.numbered_section_score(text)

        score += self.chapter_score(text)

        score += self.dotted_leader_score(text)


        return round(

            min(score, 1.0),

            2

        )


    # --------------------------------------------------
    # CHECK IF PAGE LOOKS LIKE A TOC
    # --------------------------------------------------

    def is_toc_candidate(
        self,
        text: str,
        threshold: float = 0.35
    ) -> bool:

        """
        Determine whether a page
        looks structurally similar
        to a Table of Contents page.
        """

        score = self.calculate_score(text)


        return score >= threshold


    # --------------------------------------------------
    # FIND FIRST TOC PAGE
    # --------------------------------------------------

    def find_first_toc_page(
        self,
        page_text: dict,
        max_pages: int = 15,
        threshold: float = 0.50
    ):

        """
        Search the beginning of the PDF
        and find the strongest TOC candidate.
        """

        candidates = []


        pages_to_check = min(

            max_pages,

            len(page_text)

        )


        for page_number in range(

            pages_to_check

        ):


            text = page_text.get(

                page_number,

                ""

            )


            if not text.strip():

                continue


            score = self.calculate_score(

                text

            )


            candidates.append(

                {

                    "page": page_number,

                    "score": score,

                    "text": text

                }

            )


        if not candidates:

            return None


        best_candidate = max(

            candidates,

            key=lambda item:

            item["score"]

        )


        if (

            best_candidate["score"]

            >= threshold

        ):

            return best_candidate


        return None


    # --------------------------------------------------
    # FIND CONTINUOUS TOC PAGES
    # --------------------------------------------------

    def find_toc_pages(
        self,
        page_text: dict,
        first_toc_page: int,
        continuation_threshold: float = 0.30,
        max_toc_pages: int = 10
    ) -> list:

        """
        Starting from the first TOC page,
        detect consecutive pages that also
        appear to belong to the TOC.

        Example:

        Page 2 → TOC

        Page 3 → TOC continuation

        Page 4 → TOC continuation

        Page 5 → Introduction

        Result:

        [2, 3, 4]
        """

        toc_pages = [

            first_toc_page

        ]


        current_page = (

            first_toc_page + 1

        )


        pages_checked = 1


        while (

            current_page < len(page_text)

            and

            pages_checked < max_toc_pages

        ):


            text = page_text.get(

                current_page,

                ""

            )


            score = self.calculate_score(

                text

            )


            # ------------------------------------------------
            # CONTINUATION PAGE
            # ------------------------------------------------

            if (

                text.strip()

                and

                score >= continuation_threshold

            ):


                toc_pages.append(

                    current_page

                )


                current_page += 1

                pages_checked += 1


            # ------------------------------------------------
            # TOC ENDED
            # ------------------------------------------------

            else:

                break


        return toc_pages


    # --------------------------------------------------
    # COMBINE TOC TEXT
    # --------------------------------------------------

    def combine_toc_text(
        self,
        page_text: dict,
        toc_pages: list
    ) -> str:

        """
        Combine text from all detected
        TOC pages.
        """

        toc_text_parts = []


        for page_number in toc_pages:


            text = page_text.get(

                page_number,

                ""

            )


            if text.strip():

                toc_text_parts.append(

                    text

                )


        return "\n\n".join(

            toc_text_parts

        )


    # --------------------------------------------------
    # MAIN DETECTION METHOD
    # --------------------------------------------------

    def detect(
        self,
        pdf_data: dict,
        max_search_pages: int = 15,
        detection_threshold: float = 0.50,
        continuation_threshold: float = 0.30,
        max_toc_pages: int = 10
    ) -> dict:

        """
        Main public method.

        Workflow:

        1. Search beginning of PDF.

        2. Find strongest TOC page.

        3. Check following pages for
           TOC continuation.

        4. Combine all TOC text.

        5. Return structured result.
        """

        page_text = pdf_data.get(

            "page_text",

            {}

        )


        if not page_text:

            return {

                "toc_found": False,

                "confidence": 0.0,

                "toc_pages": [],

                "toc_text": ""

            }


        # ----------------------------------------------
        # STEP 1
        # FIND FIRST TOC PAGE
        # ----------------------------------------------

        first_toc = (

            self.find_first_toc_page(

                page_text=page_text,

                max_pages=max_search_pages,

                threshold=detection_threshold

            )

        )


        if first_toc is None:

            return {

                "toc_found": False,

                "confidence": 0.0,

                "toc_pages": [],

                "toc_text": ""

            }


        # ----------------------------------------------
        # STEP 2
        # FIND TOC CONTINUATION PAGES
        # ----------------------------------------------

        toc_pages = (

            self.find_toc_pages(

                page_text=page_text,

                first_toc_page=first_toc["page"],

                continuation_threshold=(
                    continuation_threshold
                ),

                max_toc_pages=max_toc_pages

            )

        )


        # ----------------------------------------------
        # STEP 3
        # COMBINE TOC TEXT
        # ----------------------------------------------

        combined_toc_text = (

            self.combine_toc_text(

                page_text=page_text,

                toc_pages=toc_pages

            )

        )


        # ----------------------------------------------
        # STEP 4
        # FINAL RESULT
        # ----------------------------------------------

        return {

            "toc_found": True,

            "confidence":

                first_toc["score"],

            "toc_pages":

                toc_pages,

            "toc_text":

                combined_toc_text

        }


class SectionDetector:
    """Compatibility facade for the existing section-classifier API."""

    def __init__(self):
        from modules.document.pdf_reader import PDFReader
        from modules.structure.section_extractor import SectionExtractor
        from modules.structure.section_mapper import SectionMapper
        from modules.structure.toc_parser import TOCParser

        self.pdfreader = PDFReader()
        self.toc_detector = TOCDetector()
        self.toc_parser = TOCParser()
        self.section_mapper = SectionMapper()
        self.section_extractor = SectionExtractor()

    def final_section_output(self, pdf_path):
        pdf_path = Path(pdf_path)
        pdf_data = self.pdfreader.get_pdf_data(pdf_path)
        toc_result = self.toc_detector.detect(pdf_data)
        parsed_result = self.toc_parser.parse(toc_result)
        mapped_result = self.section_mapper.map_sections(parsed_result, pdf_data, toc_result)
        return {
            "metadata": {
                "filename": pdf_data.get("filename", pdf_path.name),
                "resolved_path": pdf_data.get("resolved_path", str(pdf_path.resolve())),
                "num_pages": pdf_data.get("num_pages", 0),
            },
            "sections": self.section_extractor.extract_sections(
                pdf_data,
                mapped_result.get("sections", []),
            ),
        }

    def call_llm_for_structure(self, json_data):
        return self.toc_detector.detect(json_data)

    def toc_json(self, page_content):
        if isinstance(page_content, dict) and "toc_found" in page_content:
            return self.toc_parser.parse(page_content)
        return {"sections": []}

    def classify_json(self, toc_json, json_data):
        mapped_result = self.section_mapper.map_sections(
            toc_json,
            json_data,
            json_data.get("toc", {}),
        )
        return {
            "metadata": {
                "filename": json_data.get("filename", "unknown_document"),
                "num_pages": json_data.get("num_pages", 0),
            },
            "sections": self.section_extractor.extract_sections(
                json_data,
                mapped_result.get("sections", []),
            ),
        }


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":

    from pathlib import Path

    from modules.document.pdf_reader import PDFReader


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


    # ----------------------------------------------
    # READ PDF
    # ----------------------------------------------

    reader = PDFReader()


    pdf_data = (

        reader.get_pdf_data(

            pdf_path

        )

    )


    # ----------------------------------------------
    # DETECT TOC
    # ----------------------------------------------

    detector = TOCDetector()


    result = detector.detect(

        pdf_data

    )


    # ----------------------------------------------
    # PRINT RESULT
    # ----------------------------------------------

    print(

        "\n--- TOC DETECTION RESULT ---"

    )


    print(

        "TOC Found:",

        result["toc_found"]

    )


    print(

        "Confidence:",

        result["confidence"]

    )


    print(

        "TOC Pages:",

        result["toc_pages"]

    )


    print(

        "\n--- COMBINED TOC TEXT ---\n"

    )


    print(

        result["toc_text"][:5000]

    )