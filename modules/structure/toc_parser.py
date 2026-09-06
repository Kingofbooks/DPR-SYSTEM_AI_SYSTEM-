import re


class TOCParser:

    def __init__(self):

        print("TOC Parser initialized.")


    def clean_line(
        self,
        line: str
    ) -> str:

        """
        Clean OCR artifacts and
        normalize whitespace.
        """

        line = line.strip()

        # Remove repeated whitespace
        line = re.sub(

            r"\s+",

            " ",

            line

        )

        return line


    def extract_page_reference(
        self,
        line: str
    ):

        """
        Extract page references.

        Examples:

        1
        10
        1-5
        ES-1
        ES-1 to ES-13
        Appendix.E. 1-2
        """

        patterns = [

            # ES-1
            r"\b[A-Z]{1,5}\s*[-–—]\s*\d+\b",

            # ES-1 to ES-13
            r"\b[A-Z]{1,5}\s*[-–—]\s*\d+\s+to\s+[A-Z]{1,5}\s*[-–—]\s*\d+\b",

            # 1-5
            r"\b\d+\s*[-–—]\s*\d+\b",

            # Single page number
            r"\b\d{1,4}\b$"

        ]


        for pattern in patterns:

            matches = re.findall(

                pattern,

                line,

                flags=re.IGNORECASE

            )


            if matches:

                return matches[-1]


        return None


    def extract_section_id(
        self,
        line: str
    ):

        """
        Extract section identifiers.

        Examples:

        1.
        1.1
        E.1
        E.13(A)
        Chapter 1
        """

        patterns = [

            r"^\s*([A-Z]\.\d+(?:\([A-Z]\))?)",

            r"^\s*(\d+\.\d+)",

            r"^\s*(\d+\.)",

            r"^\s*(Chapter\s+\d+)",

        ]


        for pattern in patterns:

            match = re.search(

                pattern,

                line,

                flags=re.IGNORECASE

            )


            if match:

                return match.group(1)


        return None


    def remove_page_reference(
        self,
        line: str,
        page_reference
    ):

        """
        Remove page reference
        from the section title.
        """

        if not page_reference:

            return line


        return line.replace(

            page_reference,

            ""

        ).strip()


    def remove_section_id(
        self,
        line: str,
        section_id
    ):

        """
        Remove section identifier
        from the line.
        """

        if not section_id:

            return line


        return line.replace(

            section_id,

            "",

            1

        ).strip()


    def parse_line(
        self,
        line: str
    ):

        """
        Parse a potential TOC line.
        """

        line = self.clean_line(line)


        if not line:

            return None


        section_id = self.extract_section_id(

            line

        )


        page_reference = self.extract_page_reference(

            line

        )


        # A valid TOC section normally
        # needs at least one identifier
        # or page reference.

        if not section_id:

            return None


        title = line


        title = self.remove_section_id(

            title,

            section_id

        )


        if page_reference:

            title = self.remove_page_reference(

                title,

                page_reference

            )


        title = title.strip(

            "-–—. "

        )


        # Avoid empty titles

        if not title:

            return None


        return {

            "section_id": section_id,

            "title": title,

            "page_reference": page_reference

        }


    def parse(
        self,
        toc_result: dict
    ):

        """
        Parse TOC detection output.

        Input:
            Output from TOCDetector

        Output:
            Structured sections
        """


        if not toc_result.get(

            "toc_found",

            False

        ):

            return {

                "sections": []

            }


        toc_text = toc_result.get(

            "toc_text",

            ""

        )


        lines = toc_text.splitlines()


        sections = []


        for line in lines:


            parsed_section = self.parse_line(

                line

            )


            if parsed_section:

                sections.append(

                    parsed_section

                )


        return {

            "sections": sections

        }


def main():


    from pathlib import Path

    from modules.document.pdf_reader import (
        PDFReader
    )

    from modules.structure.toc_detector import (
        TOCDetector
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


    reader = PDFReader()


    pdf_data = reader.get_pdf_data(

        pdf_path

    )


    detector = TOCDetector()


    toc_result = detector.detect(

        pdf_data

    )


    parser = TOCParser()


    result = parser.parse(

        toc_result

    )


    print(

        "\n--- PARSED TOC ---\n"

    )


    for section in result["sections"]:

        print(section)


if __name__ == "__main__":

    main()