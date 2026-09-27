from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

import pymupdf
import pytesseract

from PIL import Image


class PDFReader:
    """
    High-performance PDF reader for the DPR AI System.

    Extraction strategy:

        PDF
         |
         +--> Native text extraction
         |
         +--> If text is insufficient
                |
                +--> OCR

    OCR is parallelized across pages that require it.

    The public interface remains compatible with the existing
    DocumentProcessor:

        get_pdf_data(...)
        extract_text(...)
        extract_page_text(...)
    """

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        tesseract_path: str | None = None,
        ocr_workers: int | None = None,
        ocr_zoom: float = 2.0,
        cache_enabled: bool = True,
        cache_directory: str | Path = "data/cache/pdf_reader",
    ):

        print("PDF Reader initialized.")

        # --------------------------------------------------------
        # TESSERACT
        # --------------------------------------------------------

        if tesseract_path is None:

            tesseract_path = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )

        tesseract_path = Path(tesseract_path)

        if tesseract_path.exists():

            pytesseract.pytesseract.tesseract_cmd = (
                str(tesseract_path)
            )

            self.ocr_available = True

        else:

            self.ocr_available = False

            print(
                "Warning: Tesseract OCR was not found."
            )

        # --------------------------------------------------------
        # OCR CONFIGURATION
        # --------------------------------------------------------

        if ocr_workers is None:

            cpu_count = os.cpu_count() or 4

            # Avoid creating too many Tesseract processes.
            # 4 is usually a good starting point.
            self.ocr_workers = min(
                4,
                max(1, cpu_count)
            )

        else:

            self.ocr_workers = max(
                1,
                int(ocr_workers)
            )

        self.ocr_zoom = float(
            ocr_zoom
        )

        # --------------------------------------------------------
        # CACHE
        # --------------------------------------------------------

        self.cache_enabled = cache_enabled

        self.cache_directory = Path(
            cache_directory
        )

        if self.cache_enabled:

            self.cache_directory.mkdir(
                parents=True,
                exist_ok=True
            )

        print(
            f"OCR workers: {self.ocr_workers}"
        )

        print(
            f"OCR zoom: {self.ocr_zoom}"
        )

        print(
            f"OCR cache: "
            f"{'enabled' if self.cache_enabled else 'disabled'}"
        )

    # ============================================================
    # VALIDATE PDF
    # ============================================================

    def validate_pdf_path(
        self,
        path: str | Path
    ) -> Path:

        path = (
            Path(path)
            .expanduser()
            .resolve()
        )

        if not path.exists():

            raise FileNotFoundError(
                f"PDF file not found:\n{path}"
            )

        if not path.is_file():

            raise ValueError(
                f"Path is not a file:\n{path}"
            )

        if path.suffix.lower() != ".pdf":

            raise ValueError(
                f"File is not a PDF:\n{path}"
            )

        return path

    # ============================================================
    # FILE CACHE KEY
    # ============================================================

    def get_cache_key(
        self,
        path: Path
    ) -> str:

        """
        Generate a stable cache key from:

        - absolute PDF path
        - file size
        - modification time

        This means the cache automatically becomes invalid
        when the PDF changes.
        """

        stat = path.stat()

        identity = (
            f"{path.resolve()}|"
            f"{stat.st_size}|"
            f"{stat.st_mtime_ns}"
        )

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:24]

    # ============================================================
    # CACHE PATH
    # ============================================================

    def get_cache_path(
        self,
        pdf_path: Path
    ) -> Path:

        cache_key = self.get_cache_key(
            pdf_path
        )

        return (
            self.cache_directory
            / f"{cache_key}.json"
        )

    # ============================================================
    # LOAD CACHE
    # ============================================================

    def load_cache(
        self,
        pdf_path: Path
    ) -> dict | None:

        if not self.cache_enabled:

            return None

        cache_path = self.get_cache_path(
            pdf_path
        )

        if not cache_path.exists():

            return None

        try:

            with open(
                cache_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            # Basic validation
            if (
                data.get("resolved_path")
                != str(pdf_path)
            ):

                return None

            print()
            print(
                "PDF CACHE HIT"
            )

            print(
                f"Cache: {cache_path}"
            )

            return data

        except Exception as error:

            print(
                f"Warning: Could not load PDF cache: "
                f"{error}"
            )

            return None

    # ============================================================
    # SAVE CACHE
    # ============================================================

    def save_cache(
        self,
        pdf_path: Path,
        data: dict
    ) -> None:

        if not self.cache_enabled:

            return

        cache_path = self.get_cache_path(
            pdf_path
        )

        try:

            with open(
                cache_path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    ensure_ascii=False
                )

            print()
            print(
                "PDF extraction cached:"
            )

            print(
                cache_path
            )

        except Exception as error:

            print(
                f"Warning: Could not save PDF cache: "
                f"{error}"
            )

    # ============================================================
    # NATIVE TEXT EXTRACTION
    # ============================================================

    def extract_native_text(
        self,
        page
    ) -> str:

        try:

            text = page.get_text(
                "text"
            )

        except Exception:

            text = page.get_text()

        if not text:

            return ""

        return text.strip()

    # ============================================================
    # OCR IMAGE CREATION
    # ============================================================

    def render_page_for_ocr(
        self,
        pdf_path: Path,
        page_number: int
    ) -> Image.Image:

        """
        Render one PDF page into a PIL image.

        The PDF is opened independently inside the worker.
        This avoids sharing PyMuPDF page objects between
        threads.
        """

        with pymupdf.open(
            pdf_path
        ) as document:

            page = document[
                page_number
            ]

            matrix = pymupdf.Matrix(
                self.ocr_zoom,
                self.ocr_zoom
            )

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            image = Image.frombytes(
                "RGB",
                (
                    pixmap.width,
                    pixmap.height
                ),
                pixmap.samples
            )

            return image

    # ============================================================
    # OCR ONE PAGE
    # ============================================================

    def ocr_page(
        self,
        pdf_path: Path,
        page_number: int
    ) -> tuple[int, str]:

        if not self.ocr_available:

            raise RuntimeError(
                "OCR requested but Tesseract "
                "is not available."
            )

        try:

            image = self.render_page_for_ocr(
                pdf_path,
                page_number
            )

            text = pytesseract.image_to_string(
                image,
                lang="eng"
            )

            text = (
                text.strip()
                if text
                else ""
            )

            return (
                page_number,
                text
            )

        except Exception as error:

            raise RuntimeError(
                f"OCR failed on page "
                f"{page_number + 1}: "
                f"{error}"
            )

    # ============================================================
    # EXTRACT ONE PAGE
    # ============================================================

    def extract_page_text(
        self,
        page,
        allow_ocr: bool = False,
        minimum_text_length: int = 50
    ) -> tuple[str, str]:

        """
        Extract one page.

        Native text is ALWAYS attempted first.

        OCR is only attempted when:

            allow_ocr == True

        AND

            native text is too short.
        """

        native_text = (
            self.extract_native_text(
                page
            )
        )

        # --------------------------------------------------------
        # NATIVE TEXT IS GOOD
        # --------------------------------------------------------

        if len(native_text) >= minimum_text_length:

            return (
                native_text,
                "text"
            )

        # --------------------------------------------------------
        # OCR FALLBACK
        # --------------------------------------------------------

        if allow_ocr and self.ocr_available:

            # This method is primarily used for direct calls.
            # Bulk extraction uses the parallel OCR path below.

            pdf_document = page.parent

            if pdf_document is not None:

                try:

                    matrix = pymupdf.Matrix(
                        self.ocr_zoom,
                        self.ocr_zoom
                    )

                    pixmap = page.get_pixmap(
                        matrix=matrix,
                        alpha=False
                    )

                    image = Image.frombytes(
                        "RGB",
                        (
                            pixmap.width,
                            pixmap.height
                        ),
                        pixmap.samples
                    )

                    ocr_text = (
                        pytesseract.image_to_string(
                            image,
                            lang="eng"
                        )
                        .strip()
                    )

                    if len(ocr_text) > len(
                        native_text
                    ):

                        return (
                            ocr_text,
                            "ocr"
                        )

                except Exception as error:

                    print(
                        f"Warning: OCR failed: "
                        f"{error}"
                    )

        # --------------------------------------------------------
        # RETURN BEST AVAILABLE TEXT
        # --------------------------------------------------------

        return (
            native_text,
            "text"
        )

    # ============================================================
    # PARALLEL OCR
    # ============================================================

    def extract_ocr_pages_parallel(
        self,
        pdf_path: Path,
        page_numbers: list[int]
    ) -> dict[int, str]:

        """
        OCR multiple pages concurrently.

        Each worker independently opens the PDF.
        This is safer with PyMuPDF on Windows than sharing
        page/document objects between threads.
        """

        if not page_numbers:

            return {}

        if not self.ocr_available:

            print(
                "OCR unavailable. "
                "Skipping OCR pages."
            )

            return {
                page_number: ""
                for page_number in page_numbers
            }

        print()
        print(
            f"OCR required for "
            f"{len(page_numbers)} pages."
        )

        print(
            f"Running "
            f"{self.ocr_workers} "
            f"parallel OCR workers..."
        )

        results = {}

        with ThreadPoolExecutor(
            max_workers=self.ocr_workers
        ) as executor:

            futures = {

                executor.submit(
                    self.ocr_page,
                    pdf_path,
                    page_number
                ): page_number

                for page_number
                in page_numbers

            }

            completed = 0

            total = len(
                futures
            )

            for future in as_completed(
                futures
            ):

                page_number = futures[
                    future
                ]

                try:

                    (
                        page_number,
                        text
                    ) = future.result()

                    results[
                        page_number
                    ] = text

                except Exception as error:

                    print(
                        f"OCR ERROR | "
                        f"Page "
                        f"{page_number + 1}: "
                        f"{error}"
                    )

                    results[
                        page_number
                    ] = ""

                completed += 1

                print(
                    f"OCR "
                    f"{completed}/"
                    f"{total} | "
                    f"Page "
                    f"{page_number + 1}"
                )

        return results

    # ============================================================
    # EXTRACT ENTIRE PDF
    # ============================================================

    def extract_text(
        self,
        path: str | Path,
        ocr_pages: Iterable[int] | None = None,
        minimum_text_length: int = 50,
        use_parallel_ocr: bool = True,
    ):

        """
        Extract the entire PDF.

        IMPORTANT:

        Native extraction happens first for EVERY page.

        OCR is then performed only for pages where:

            len(native_text) < minimum_text_length

        and the page is allowed to use OCR.

        If ocr_pages is None:

            OCR fallback is allowed automatically for
            pages with insufficient native text.

        If ocr_pages is supplied:

            Only those page numbers are eligible for OCR.

        This preserves compatibility with the existing
        DocumentProcessor.
        """

        pdf_path = self.validate_pdf_path(
            path
        )

        # --------------------------------------------------------
        # CACHE
        # --------------------------------------------------------

        cached = self.load_cache(
            pdf_path
        )

        if cached is not None:

            return (
                cached["full_text"],
                {
                    int(k): v
                    for k, v
                    in cached["page_text"].items()
                },
                cached["num_pages"],
                {
                    int(k): v
                    for k, v
                    in cached[
                        "page_metadata"
                    ].items()
                }
            )

        # --------------------------------------------------------
        # OCR PAGE CONFIGURATION
        # --------------------------------------------------------

        if ocr_pages is None:

            explicit_ocr_pages = None

        else:

            explicit_ocr_pages = set(
                int(page)
                for page in ocr_pages
            )

        page_text: dict[int, str] = {}

        page_metadata: dict[int, dict] = {}

        pages_requiring_ocr = []

        # --------------------------------------------------------
        # PASS 1
        # NATIVE EXTRACTION
        # --------------------------------------------------------

        print()

        print(
            "PASS 1: NATIVE TEXT EXTRACTION"
        )

        try:

            with pymupdf.open(
                pdf_path
            ) as document:

                num_pages = len(
                    document
                )

                print(
                    f"\nProcessing PDF with "
                    f"{num_pages} pages..."
                )

                for page_number, page in enumerate(
                    document
                ):

                    native_text = (
                        self.extract_native_text(
                            page
                        )
                    )

                    page_text[
                        page_number
                    ] = native_text

                    native_length = len(
                        native_text
                    )

                    # ------------------------------------------------
                    # DETERMINE OCR ELIGIBILITY
                    # ------------------------------------------------

                    needs_ocr = (
                        native_length
                        < minimum_text_length
                    )

                    if (
                        explicit_ocr_pages
                        is not None
                    ):

                        allow_ocr = (
                            page_number
                            in explicit_ocr_pages
                        )

                    else:

                        allow_ocr = True

                    if (
                        needs_ocr
                        and allow_ocr
                        and self.ocr_available
                    ):

                        pages_requiring_ocr.append(
                            page_number
                        )

                    page_metadata[
                        page_number
                    ] = {

                        "extraction_method":
                            "text",

                        "native_text_length":
                            native_length,

                        "text_length":
                            native_length,

                        "ocr_attempted":
                            False,

                        "ocr_used":
                            False

                    }

                    print(
                        f"Page "
                        f"{page_number + 1}/"
                        f"{num_pages}"
                        f" | Method: TEXT"
                        f" | Characters: "
                        f"{native_length}"
                    )

        except Exception as error:

            raise RuntimeError(
                f"Failed to read PDF: "
                f"{error}"
            )

        # --------------------------------------------------------
        # PASS 2
        # PARALLEL OCR
        # --------------------------------------------------------

        if (
            pages_requiring_ocr
            and self.ocr_available
        ):

            print()

            print(
                "PASS 2: PARALLEL OCR"
            )

            if use_parallel_ocr:

                ocr_results = (
                    self.extract_ocr_pages_parallel(
                        pdf_path,
                        pages_requiring_ocr
                    )
                )

            else:

                ocr_results = {}

                for page_number in (
                    pages_requiring_ocr
                ):

                    _, text = self.ocr_page(
                        pdf_path,
                        page_number
                    )

                    ocr_results[
                        page_number
                    ] = text

            # ----------------------------------------------------
            # MERGE OCR RESULTS
            # ----------------------------------------------------

            for page_number in (
                pages_requiring_ocr
            ):

                native_text = page_text.get(
                    page_number,
                    ""
                )

                ocr_text = ocr_results.get(
                    page_number,
                    ""
                )

                page_metadata[
                    page_number
                ][
                    "ocr_attempted"
                ] = True

                # Use OCR only if it provides more
                # useful content.
                if len(ocr_text) > len(
                    native_text
                ):

                    page_text[
                        page_number
                    ] = ocr_text

                    page_metadata[
                        page_number
                    ][
                        "extraction_method"
                    ] = "ocr"

                    page_metadata[
                        page_number
                    ][
                        "ocr_used"
                    ] = True

                    page_metadata[
                        page_number
                    ][
                        "text_length"
                    ] = len(ocr_text)

                else:

                    page_metadata[
                        page_number
                    ][
                        "text_length"
                    ] = len(native_text)

        # --------------------------------------------------------
        # BUILD FULL TEXT
        # --------------------------------------------------------

        full_text_parts = []

        for page_number in range(
            num_pages
        ):

            full_text_parts.append(
                page_text.get(
                    page_number,
                    ""
                )
            )

        full_text = "\n".join(
            full_text_parts
        )

        # --------------------------------------------------------
        # FINAL OCR STATISTICS
        # --------------------------------------------------------

        ocr_used_pages = [

            page_number

            for page_number, metadata
            in page_metadata.items()

            if metadata.get(
                "ocr_used",
                False
            )

        ]

        print()

        print(
            "EXTRACTION SUMMARY"
        )

        print(
            f"Pages: {num_pages}"
        )

        print(
            f"Native pages: "
            f"{num_pages - len(ocr_used_pages)}"
        )

        print(
            f"OCR pages: "
            f"{len(ocr_used_pages)}"
        )

        print(
            f"Total characters: "
            f"{len(full_text)}"
        )

        # --------------------------------------------------------
        # SAVE CACHE
        # --------------------------------------------------------

        result = {

            "filename":
                pdf_path.name,

            "resolved_path":
                str(pdf_path),

            "num_pages":
                num_pages,

            "full_text":
                full_text,

            "page_text":
                {
                    str(k): v
                    for k, v in page_text.items()
                },

            "page_metadata":
                {
                    str(k): v
                    for k, v in page_metadata.items()
                }

        }

        self.save_cache(
            pdf_path,
            result
        )

        return (
            full_text,
            page_text,
            num_pages,
            page_metadata
        )

    # ============================================================
    # STRUCTURED PDF DATA
    # ============================================================

    def get_pdf_data(
        self,
        path: str | Path,
        ocr_pages: Iterable[int] | None = None,
        minimum_text_length: int = 50,
        use_parallel_ocr: bool = True,
    ):

        """
        Main public API used by DocumentProcessor.
        """

        (

            full_text,

            page_text,

            num_pages,

            page_metadata

        ) = self.extract_text(

            path=path,

            ocr_pages=ocr_pages,

            minimum_text_length=(
                minimum_text_length
            ),

            use_parallel_ocr=(
                use_parallel_ocr
            )

        )

        pdf_path = self.validate_pdf_path(
            path
        )

        return {

            "filename":
                pdf_path.name,

            "resolved_path":
                str(pdf_path),

            "num_pages":
                num_pages,

            "full_text":
                full_text,

            "page_text":
                page_text,

            "page_metadata":
                page_metadata

        }


# ================================================================
# TEST
# ================================================================

def main():

    print()

    print("=" * 60)

    print(
        "TESTING OPTIMIZED PDF READER"
    )

    print("=" * 60)

    reader = PDFReader(
        ocr_workers=4,
        ocr_zoom=2.0,
        cache_enabled=True
    )

    pdf_path = (

        Path(__file__)
        .resolve()
        .parents[2]

        / "data"
        / "raw"
        / "DPR of Road.pdf"

    )

    result = reader.get_pdf_data(
        path=pdf_path,

        # Let the reader automatically determine
        # which pages need OCR.
        ocr_pages=None,

        minimum_text_length=50,

        use_parallel_ocr=True
    )

    print()

    print("=" * 60)

    print(
        "PDF READER TEST COMPLETE"
    )

    print("=" * 60)

    print()

    print(
        f"Filename: "
        f"{result['filename']}"
    )

    print(
        f"Pages: "
        f"{result['num_pages']}"
    )

    print(
        f"Characters: "
        f"{len(result['full_text'])}"
    )


if __name__ == "__main__":

    main()