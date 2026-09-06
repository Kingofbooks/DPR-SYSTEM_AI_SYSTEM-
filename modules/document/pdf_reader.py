from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


class PDFReader:

    def __init__(self):

        print("PDF Reader initialized.")

        # Windows Tesseract path
        tesseract_path = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        if Path(tesseract_path).exists():

            pytesseract.pytesseract.tesseract_cmd = (
                tesseract_path
            )

    def extract_text_with_ocr(
        self,
        page
    ):

        """
        Convert a PDF page into an image
        and extract text using OCR.
        """

        zoom = 2

        matrix = pymupdf.Matrix(
            zoom,
            zoom
        )

        pixmap = page.get_pixmap(
            matrix=matrix
        )

        # Handle RGB / RGBA images
        if pixmap.alpha:

            image = Image.frombytes(

                "RGBA",

                (
                    pixmap.width,
                    pixmap.height
                ),

                pixmap.samples

            ).convert("RGB")

        else:

            image = Image.frombytes(

                "RGB",

                (
                    pixmap.width,
                    pixmap.height
                ),

                pixmap.samples

            )

        text = pytesseract.image_to_string(

            image,

            lang="eng"

        )

        return text.strip()


    def extract_text_from_page(
        self,
        page
    ):

        """
        Extract text from one PDF page.

        Priority:

        1. Native PDF text
        2. OCR fallback
        3. Empty page
        """

        native_text = page.get_text().strip()

        # ---------------------------------
        # CASE 1
        # Native text extraction succeeded
        # ---------------------------------

        if len(native_text) >= 50:

            return (

                native_text,

                "text",

                False

            )


        # ---------------------------------
        # CASE 2
        # Native extraction insufficient
        # Use OCR
        # ---------------------------------

        ocr_text = self.extract_text_with_ocr(

            page

        )


        if len(ocr_text) > 0:

            return (

                ocr_text,

                "ocr",

                True

            )


        # ---------------------------------
        # CASE 3
        # No usable text
        # ---------------------------------

        return (

            "",

            "empty",

            True

        )


    def extract_text(
        self,
        path
    ):

        """
        Extract text from all pages.

        Uses:

        1. Native PDF text extraction
        2. OCR fallback

        Returns:

        full_text
        page_text
        num_pages
        page_metadata
        """

        path = Path(path).expanduser().resolve()


        if not path.exists():

            raise FileNotFoundError(

                f"PDF file not found: {path}"

            )


        page_text = {}

        page_metadata = {}

        full_text_parts = []


        try:

            with pymupdf.open(path) as document:


                num_pages = len(document)


                print(

                    f"\nProcessing PDF with "

                    f"{num_pages} pages..."

                )


                for page_number, page in enumerate(document):


                    (
                        text,
                        method,
                        ocr_attempted

                    ) = self.extract_text_from_page(

                        page

                    )


                    page_text[page_number] = text


                    page_metadata[page_number] = {

                        "extraction_method": method,

                        "text_length": len(text),

                        "ocr_attempted": ocr_attempted

                    }


                    full_text_parts.append(text)


                    print(

                        f"Page "

                        f"{page_number + 1}/"

                        f"{num_pages} | "

                        f"Method: "

                        f"{method.upper()} | "

                        f"Characters: "

                        f"{len(text)}"

                    )


            full_text = "\n".join(

                full_text_parts

            )


            return (

                full_text,

                page_text,

                num_pages,

                page_metadata

            )


        except Exception as error:


            raise RuntimeError(

                f"Failed to read PDF: "

                f"{error}"

            )


    def get_pdf_data(
        self,
        path
    ):

        """
        Main public method.

        Returns structured PDF data.
        """


        (

            full_text,

            page_text,

            num_pages,

            page_metadata

        ) = self.extract_text(

            path

        )


        return {

            "filename": Path(path).name,

            "num_pages": num_pages,

            "full_text": full_text,

            "page_text": page_text,

            "page_metadata": page_metadata

        }


def main():


    reader = PDFReader()


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


    result = reader.get_pdf_data(

        pdf_path

    )


    print(

        "\n--- PDF INFORMATION ---"

    )


    print(

        "Filename:",

        result["filename"]

    )


    print(

        "Pages:",

        result["num_pages"]

    )


    print(

        "\n--- FIRST PAGE ---"

    )


    print(

        result["page_text"][0][:1500]

    )


    print(

        "\n--- EXTRACTION SUMMARY ---"

    )


    text_pages = sum(

        1

        for metadata in result[
            "page_metadata"
        ].values()

        if metadata[
            "extraction_method"
        ] == "text"

    )


    ocr_pages = sum(

        1

        for metadata in result[
            "page_metadata"
        ].values()

        if metadata[
            "extraction_method"
        ] == "ocr"

    )


    empty_pages = sum(

        1

        for metadata in result[
            "page_metadata"
        ].values()

        if metadata[
            "extraction_method"
        ] == "empty"

    )


    print(

        f"Native Text Pages: "

        f"{text_pages}"

    )


    print(

        f"OCR Pages: "

        f"{ocr_pages}"

    )


    print(

        f"Empty Pages: "

        f"{empty_pages}"

    )


if __name__ == "__main__":

    main()