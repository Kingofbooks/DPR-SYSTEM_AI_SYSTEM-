import re
from difflib import SequenceMatcher


class SectionMapper:

    def __init__(self):

        print("Section Mapper initialized.")


    def normalize_text(
        self,
        text: str
    ) -> str:

        """
        Normalize text to make OCR matching
        more reliable.
        """

        text = text.lower()

        # Normalize different dash types
        text = text.replace("–", "-")
        text = text.replace("—", "-")

        # Remove extra whitespace
        text = re.sub(
            r"\s+",
            " ",
            text
        )

        # Remove most punctuation
        text = re.sub(
            r"[^a-z0-9.\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def normalize_section_id(
        self,
        section_id: str
    ) -> str:

        """
        Normalize section IDs.

        Example:

        E.13(A)
        e.13(a)
        E.13 A

        become comparable.
        """

        if not section_id:
            return ""

        section_id = section_id.lower()

        section_id = section_id.replace(
            " ",
            ""
        )

        return section_id


    def calculate_similarity(
        self,
        title: str,
        page_text: str
    ) -> float:

        """
        Calculate similarity between
        section title and page text.
        """

        normalized_title = self.normalize_text(
            title
        )

        normalized_page = self.normalize_text(
            page_text
        )

        if not normalized_title:
            return 0.0

        if not normalized_page:
            return 0.0


        # Exact title exists somewhere
        if normalized_title in normalized_page:

            return 1.0


        title_words = normalized_title.split()

        if not title_words:

            return 0.0


        # Word overlap score
        matched_words = 0

        for word in title_words:

            if len(word) <= 2:
                continue

            if word in normalized_page:

                matched_words += 1


        valid_words = [

            word
            for word in title_words
            if len(word) > 2

        ]


        if not valid_words:

            return 0.0


        word_score = (

            matched_words
            / len(valid_words)

        )


        # Compare title against text chunks
        best_similarity = 0.0

        words = normalized_page.split()

        window_size = max(
            len(title_words) + 5,
            10
        )


        for i in range(

            0,

            max(
                1,
                len(words) - window_size + 1
            )

        ):

            chunk = " ".join(

                words[
                    i:
                    i + window_size
                ]

            )


            similarity = (

                SequenceMatcher(
                    None,
                    normalized_title,
                    chunk
                ).ratio()

            )


            best_similarity = max(

                best_similarity,
                similarity

            )


        # Combine scores
        final_score = (

            0.7 * word_score

            +

            0.3 * best_similarity

        )


        return round(
            final_score,
            3
        )


    def section_id_score(
        self,
        section_id: str,
        page_text: str
    ) -> float:

        """
        Check whether the section ID
        appears on the page.
        """

        if not section_id:

            return 0.0


        normalized_id = (

            self.normalize_section_id(
                section_id
            )

        )


        normalized_page = (

            self.normalize_text(
                page_text
            )

        )


        # Remove spaces for easier matching
        compact_page = normalized_page.replace(
            " ",
            ""
        )


        if normalized_id in compact_page:

            return 1.0


        return 0.0


    def find_best_page(
        self,
        section: dict,
        page_text: dict,
        start_page: int = 0,
        threshold: float = 0.45
    ) -> dict:

        """
        Find the most likely PDF page
        for a section.
        """

        section_id = section.get(
            "section_id",
            ""
        )

        title = section.get(
            "title",
            ""
        )


        best_page = None

        best_score = 0.0


        for page_number, text in page_text.items():

            # Skip TOC / initial pages
            if page_number < start_page:

                continue


            if not text.strip():

                continue


            id_score = (

                self.section_id_score(
                    section_id,
                    text
                )

            )


            title_score = (

                self.calculate_similarity(
                    title,
                    text
                )

            )


            # Section ID is strong evidence
            if id_score == 1.0:

                final_score = (

                    0.6

                    +

                    0.4 * title_score

                )

            else:

                final_score = title_score


            if final_score > best_score:

                best_score = final_score

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
                )

            }


        return {

            "pdf_page": None,

            "confidence": round(
                best_score,
                3
            )

        }


    def map_sections(
        self,
        parsed_toc: dict,
        pdf_data: dict,
        toc_result: dict = None,
        threshold: float = 0.45
    ) -> dict:

        """
        Map parsed TOC sections
        to actual PDF pages.
        """

        print(
            "\nMapping sections..."
        )


        # IMPORTANT:
        # TOCParser returns:
        #
        # {
        #     "sections": [...]
        # }

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


        # Determine where to start searching.
        #
        # We skip detected TOC pages
        # to avoid mapping sections
        # back to the Table of Contents.

        start_page = 0


        if toc_result:

            toc_pages = toc_result.get(
                "toc_pages",
                []
            )


            if toc_pages:

                start_page = (

                    max(toc_pages) + 1

                )


        mapped_sections = []


        for section in sections:


            # Safety check

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


            result = self.find_best_page(

                section=section,

                page_text=page_text,

                start_page=start_page,

                threshold=threshold

            )


            mapped_section = {

                "section_id": section_id,

                "title": title,

                "page_reference":

                    section.get(
                        "page_reference"
                    ),

                "pdf_page":

                    result["pdf_page"],

                "confidence":

                    result["confidence"]

            }


            mapped_sections.append(
                mapped_section
            )


            if (
                result["pdf_page"]
                is not None
            ):

                print(

                    f"FOUND | "

                    f"{section_id} | "

                    f"{title} | "

                    f"PDF Page "

                    f"{result['pdf_page'] + 1} | "

                    f"Confidence: "

                    f"{result['confidence']}"

                )


            else:

                print(

                    f"NOT FOUND | "

                    f"{section_id} | "

                    f"{title} | "

                    f"Best Confidence: "

                    f"{result['confidence']}"

                )


        return {

            "sections":

                mapped_sections

        }


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

        / "dpr-kjuice_copy.pdf"

    )


    # -------------------------
    # STEP 1
    # Read PDF
    # -------------------------

    reader = PDFReader()


    pdf_data = (

        reader.get_pdf_data(
            pdf_path
        )

    )


    # -------------------------
    # STEP 2
    # Detect TOC
    # -------------------------

    detector = TOCDetector()


    toc_result = (

        detector.detect(
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


    # -------------------------
    # STEP 3
    # Parse TOC
    # -------------------------

    parser = TOCParser()


    parsed_toc = (

        parser.parse(
            toc_result
        )

    )


    print(
        "\n--- PARSED SECTIONS ---"
    )


    print(

        "Sections Found:",

        len(
            parsed_toc["sections"]
        )

    )


    # -------------------------
    # STEP 4
    # Map Sections
    # -------------------------

    mapper = SectionMapper()


    result = (

        mapper.map_sections(

            parsed_toc=

                parsed_toc,

            pdf_data=

                pdf_data,

            toc_result=

                toc_result

        )

    )


    # -------------------------
    # FINAL OUTPUT
    # -------------------------

    print(
        "\n--- SECTION MAPPING ---\n"
    )


    for section in result["sections"]:

        print(section)


if __name__ == "__main__":

    main()