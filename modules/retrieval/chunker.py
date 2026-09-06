import json
import re
from pathlib import Path
from typing import Any


class DocumentChunker:
    """
    Splits extracted document sections into smaller chunks.

    Input:
        Processed document JSON produced by DocumentProcessor.

    Output:
        JSON file containing chunks with metadata.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        print("Document Chunker initialized.")

    # ============================================================
    # LOAD DOCUMENT
    # ============================================================

    def load_document(self, file_path: str) -> dict[str, Any]:
        """
        Load processed document JSON.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Processed document not found:\n{path}"
            )

        with open(path, "r", encoding="utf-8") as file:
            document = json.load(file)

        return document

    # ============================================================
    # NORMALIZE TEXT
    # ============================================================

    def normalize_text(self, text: str) -> str:
        """
        Clean extracted OCR/text before chunking.
        """

        if not text:
            return ""

        # Normalize whitespace
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove excessive spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    # ============================================================
    # SPLIT INTO PARAGRAPHS
    # ============================================================

    def split_into_paragraphs(self, text: str) -> list[str]:
        """
        Split text into meaningful paragraph-like units.
        """

        paragraphs = re.split(
            r"\n\s*\n",
            text
        )

        cleaned_paragraphs = []

        for paragraph in paragraphs:

            paragraph = paragraph.strip()

            if paragraph:
                cleaned_paragraphs.append(paragraph)

        return cleaned_paragraphs

    # ============================================================
    # SPLIT LARGE TEXT
    # ============================================================

    def split_large_text(
        self,
        text: str,
    ) -> list[str]:
        """
        Split very large text into smaller pieces.

        Tries sentence boundaries first.
        """

        if len(text) <= self.chunk_size:
            return [text]

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        chunks = []
        current_chunk = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            # If one sentence itself is too large
            if len(sentence) > self.chunk_size:

                if current_chunk:
                    chunks.append(
                        current_chunk.strip()
                    )

                    current_chunk = ""

                start = 0

                while start < len(sentence):

                    end = start + self.chunk_size

                    chunks.append(
                        sentence[start:end].strip()
                    )

                    start += (
                        self.chunk_size
                        - self.chunk_overlap
                    )

                continue

            # Add sentence if it fits
            if (
                len(current_chunk)
                + len(sentence)
                + 1
                <= self.chunk_size
            ):

                if current_chunk:
                    current_chunk += " "

                current_chunk += sentence

            else:

                if current_chunk:
                    chunks.append(
                        current_chunk.strip()
                    )

                current_chunk = sentence

        if current_chunk:
            chunks.append(
                current_chunk.strip()
            )

        return chunks

    # ============================================================
    # CREATE CHUNKS FROM SECTION
    # ============================================================

    def chunk_section(
        self,
        section: dict[str, Any],
        document_name: str,
    ) -> list[dict[str, Any]]:
        """
        Chunk a single extracted section.
        """

        # --------------------------------------------------------
        # READ SECTION DATA
        # --------------------------------------------------------

        section_id = section.get(
            "section_id",
            "unknown_section"
        )

        title = section.get(
            "title",
            "Untitled Section"
        )

        content = section.get(
            "content",
            ""
        )

        start_page = section.get(
            "start_page"
        )

        end_page = section.get(
            "end_page"
        )

        confidence = section.get(
            "confidence",
            0.0
        )

        # --------------------------------------------------------
        # NORMALIZE CONTENT
        # --------------------------------------------------------

        content = self.normalize_text(content)

        if not content:
            return []

        # --------------------------------------------------------
        # SPLIT INTO PARAGRAPHS
        # --------------------------------------------------------

        paragraphs = self.split_into_paragraphs(
            content
        )

        if not paragraphs:

            return []

        chunks = []

        current_chunk = ""

        # --------------------------------------------------------
        # BUILD CHUNKS
        # --------------------------------------------------------

        for paragraph in paragraphs:

            # Paragraph larger than chunk size
            if len(paragraph) > self.chunk_size:

                # Save current chunk first
                if current_chunk:

                    chunks.append(
                        current_chunk.strip()
                    )

                    current_chunk = ""

                large_chunks = self.split_large_text(
                    paragraph
                )

                chunks.extend(
                    large_chunks
                )

                continue

            # Paragraph fits inside current chunk
            if (
                len(current_chunk)
                + len(paragraph)
                + 2
                <= self.chunk_size
            ):

                if current_chunk:
                    current_chunk += "\n\n"

                current_chunk += paragraph

            else:

                # Save current chunk
                if current_chunk:

                    chunks.append(
                        current_chunk.strip()
                    )

                current_chunk = paragraph

        # Save final chunk
        if current_chunk:

            chunks.append(
                current_chunk.strip()
            )

        # --------------------------------------------------------
        # ADD METADATA
        # --------------------------------------------------------

        final_chunks = []

        for index, chunk_text in enumerate(chunks):

            if not chunk_text:
                continue

            chunk_id = (
                f"{document_name}"
                f"__{section_id}"
                f"__chunk_{index + 1}"
            )

            chunk = {
                "chunk_id": chunk_id,

                "document": document_name,

                "section_id": section_id,

                "section_title": title,

                "chunk_index": index + 1,

                "start_page": start_page,

                "end_page": end_page,

                "section_confidence": confidence,

                "content": chunk_text,

                "character_count": len(
                    chunk_text
                ),
            }

            final_chunks.append(chunk)

        return final_chunks

    # ============================================================
    # CHUNK DOCUMENT
    # ============================================================

    def chunk_document(
        self,
        document: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Chunk all extracted sections in a document.
        """

        metadata = document.get(
            "metadata",
            {}
        )

        document_name = metadata.get(
            "filename",
            "unknown_document"
        )

        # IMPORTANT:
        # Your DocumentProcessor stores extracted
        # sections under the "sections" key.
        sections = document.get(
            "sections",
            []
        )

        print()
        print("Chunking document...")
        print(f"Document: {document_name}")
        print(f"Sections: {len(sections)}")

        if not sections:

            print()
            print(
                "WARNING: No sections found in document."
            )

            print(
                "Expected key: 'sections'"
            )

            return []

        all_chunks = []

        # --------------------------------------------------------
        # PROCESS EACH SECTION
        # --------------------------------------------------------

        for section in sections:

            if not isinstance(section, dict):

                print(
                    "WARNING: Skipping invalid section."
                )

                continue

            section_chunks = self.chunk_section(
                section=section,
                document_name=document_name,
            )

            all_chunks.extend(
                section_chunks
            )

            print(
                f"CHUNKED | "
                f"{section.get('section_id', 'UNKNOWN')} | "
                f"{section.get('title', 'Untitled')} | "
                f"Chunks: {len(section_chunks)}"
            )

        return all_chunks

    # ============================================================
    # SAVE CHUNKS
    # ============================================================

    def save_chunks(
        self,
        chunks: list[dict[str, Any]],
        output_path: str,
    ) -> None:
        """
        Save chunks to JSON.
        """

        path = Path(output_path)

        # Create parent directories
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output = {
            "total_chunks": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunks": chunks,
        }

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                output,
                file,
                indent=4,
                ensure_ascii=False,
            )

        print()
        print("Chunks saved successfully:")
        print(path)

    # ============================================================
    # COMPLETE PIPELINE
    # ============================================================

    def process(
        self,
        input_path: str,
        output_path: str,
    ) -> list[dict[str, Any]]:
        """
        Complete chunking pipeline.
        """

        print()
        print("=" * 60)
        print("STARTING DOCUMENT CHUNKING")
        print("=" * 60)

        document = self.load_document(
            input_path
        )

        chunks = self.chunk_document(
            document
        )

        self.save_chunks(
            chunks,
            output_path
        )

        print()
        print("=" * 60)
        print("DOCUMENT CHUNKING COMPLETE")
        print("=" * 60)

        print()
        print(f"Total Chunks: {len(chunks)}")

        return chunks


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    INPUT_PATH = (
        "data/processed/DPR of Road.json"
    )

    OUTPUT_PATH = (
        "data/processed/DPR of Road_chunks.json"
    )

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = chunker.process(
        input_path=INPUT_PATH,
        output_path=OUTPUT_PATH,
    )

    # ========================================================
    # CHUNK PREVIEW
    # ========================================================

    print()
    print("=" * 60)
    print("CHUNK PREVIEW")
    print("=" * 60)

    for chunk in chunks[:5]:

        print()

        print("-" * 60)

        print(
            f"CHUNK ID: "
            f"{chunk['chunk_id']}"
        )

        print(
            f"SECTION: "
            f"{chunk['section_id']}"
        )

        print(
            f"TITLE: "
            f"{chunk['section_title']}"
        )

        print(
            f"CHUNK INDEX: "
            f"{chunk['chunk_index']}"
        )

        print(
            f"CHARACTERS: "
            f"{chunk['character_count']}"
        )

        print()

        preview = chunk["content"][:300]

        print(
            f"CONTENT PREVIEW:\n"
            f"{preview}"
        )

        print()

    print("=" * 60)