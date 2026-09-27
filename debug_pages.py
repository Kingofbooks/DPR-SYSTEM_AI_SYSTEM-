from pathlib import Path

from modules.document.pdf_reader import PDFReader


BASE_DIR = Path(__file__).resolve().parent

pdf_path = BASE_DIR / "data" / "raw" / "DPR of Road.pdf"
if not pdf_path.exists():
    pdf_path = BASE_DIR / "data" / "raw" / "Dataset" / "DPR of Road.pdf"

if not pdf_path.exists():
    raise FileNotFoundError(f"PDF file not found. Checked: {pdf_path}")

reader = PDFReader()

pdf_data = reader.get_pdf_data(
    pdf_path
)

page_text = pdf_data["page_text"]


print("\n" + "=" * 80)
print("PAGES 18-84")
print("=" * 80)


# PDF pages are zero-indexed internally.
# We want human pages 18-84.

for page_number in range(
    17,
    len(page_text)
):

    text = page_text.get(
        page_number,
        ""
    )

    print("\n" + "-" * 80)

    print(
        f"PDF PAGE: {page_number + 1}"
    )

    # Show only first 500 characters
    print(
        text[:500].replace(
            "\n",
            " "
        )
    )