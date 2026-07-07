import os
from pathlib import Path
from dotenv import load_dotenv
import fitz

load_dotenv()


class PDFReader:
    def __init__(self):
        print("Loaded PDF Reader")

    def _resolve_path(self, path):
        path = Path(path).expanduser()
        if not path.is_absolute():
            path = (Path(__file__).resolve().parents[1] / path).resolve()

        candidates = [path]
        if path.name != "sample_dpr.pdf":
            candidates.append(Path(__file__).resolve().parents[1] / "data" / "raw" / "sample_dpr.pdf")
        if path.name != "DPR_SAMPLE.pdf":
            candidates.append(Path(__file__).resolve().parents[1] / "data" / "raw" / "DPR_SAMPLE.pdf")

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return path

    def extract_text(self, path):
        """
        Extract text from every page.

        Returns
        -------
        tuple
            full_text,page_text,num_pages
        """
        page_text = {}
        full_text = ""
        resolved_path = self._resolve_path(path)

        try:
            with fitz.open(str(resolved_path)) as doc:
                num_pages = len(doc)
                for pg_num, page in enumerate(doc):
                    txt = page.get_text()
                    page_text[pg_num] = txt
                    full_text += txt
            return full_text, page_text, num_pages
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return "", {}, 0

    def get_pdf_data(self, path):
        full_text, page_text, num_pages = self.extract_text(path)

        json_txt = {
            "filename": Path(path).name,
            "resolved_path": str(self._resolve_path(path)),
            "num_pages": num_pages,
            "text": full_text,
            "page_text": page_text,
        }

        return json_txt


def main():
    pdf_reader = PDFReader()
    final_result = pdf_reader.get_pdf_data(r"F:\DPR_AI-System\data\raw\DPR_SAMPLE.pdf")
    print("\n--- FINAL JSON OUTPUT ---")
    print(final_result)


if __name__ == "__main__":
    main()
