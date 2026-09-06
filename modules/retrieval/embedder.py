import json
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer


class DocumentEmbedder:
    """
    Creates vector embeddings for document chunks.

    Each chunk is converted into a numerical vector that can
    later be used for semantic similarity search.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        print("Document Embedder initialized.")

        self.model_name = model_name

        print(f"Loading embedding model: {model_name}")

        self.model = SentenceTransformer(model_name)

        print("Embedding model loaded successfully.")


    def create_embedding_text(
        self,
        chunk: dict[str, Any]
    ) -> str:
        """
        Creates contextual text for embedding.

        Including the section title helps the embedding model
        understand the context of the chunk.
        """

        section_id = chunk.get("section_id", "")
        section_title = chunk.get("section_title", "")
        content = chunk.get("content", "")

        text = f"""
Section: {section_id}
Title: {section_title}

Content:
{content}
"""

        return text.strip()


    def embed_chunks(
        self,
        chunks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate embeddings for all document chunks.
        """

        if not chunks:
            print("WARNING: No chunks provided for embedding.")
            return []

        print()
        print("=" * 60)
        print("CREATING EMBEDDINGS")
        print("=" * 60)
        print()

        print(f"Total chunks: {len(chunks)}")
        print()

        embedded_chunks = []

        texts = []

        for chunk in chunks:

            text = self.create_embedding_text(chunk)

            texts.append(text)


        print("Generating embeddings...")

        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )


        for index, chunk in enumerate(chunks):

            embedded_chunk = chunk.copy()

            # NumPy arrays cannot be directly saved as JSON.
            embedded_chunk["embedding"] = (
                embeddings[index].tolist()
            )

            embedded_chunks.append(embedded_chunk)


        print()
        print("Embeddings created successfully.")
        print(f"Embedded chunks: {len(embedded_chunks)}")
        print(
            f"Embedding dimension: "
            f"{len(embedded_chunks[0]['embedding'])}"
        )

        return embedded_chunks


    def load_chunks(
        self,
        chunks_path: str | Path
    ) -> list[dict[str, Any]]:
        """
        Load chunks from a JSON file.
        """

        chunks_path = Path(chunks_path)

        if not chunks_path.exists():

            raise FileNotFoundError(
                f"Chunks file not found: {chunks_path}"
            )


        with open(
            chunks_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        # Support multiple possible JSON structures.

        if isinstance(data, list):

            return data


        if isinstance(data, dict):

            if "chunks" in data:

                return data["chunks"]


        raise ValueError(
            "Invalid chunks JSON format. "
            "Expected a list or dictionary containing 'chunks'."
        )


    def save_embeddings(
        self,
        embedded_chunks: list[dict[str, Any]],
        output_path: str | Path
    ) -> None:
        """
        Save embedded chunks to a JSON file.
        """

        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        data = {
            "model_name": self.model_name,
            "total_chunks": len(embedded_chunks),
            "embedding_dimension": (
                len(
                    embedded_chunks[0]["embedding"]
                )
                if embedded_chunks
                else 0
            ),
            "chunks": embedded_chunks
        }


        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )


        print()
        print("Embeddings saved successfully:")
        print(output_path)


def main():

    print()
    print("=" * 60)
    print("STARTING DOCUMENT EMBEDDING")
    print("=" * 60)


    chunks_path = Path(
        "data/processed/DPR of Road_chunks.json"
    )


    output_path = Path(
        "data/processed/DPR of Road_embeddings.json"
    )


    # --------------------------------------------------
    # INITIALIZE EMBEDDER
    # --------------------------------------------------

    embedder = DocumentEmbedder()


    # --------------------------------------------------
    # LOAD CHUNKS
    # --------------------------------------------------

    print()
    print("Loading chunks...")

    chunks = embedder.load_chunks(
        chunks_path
    )

    print(
        f"Chunks loaded: {len(chunks)}"
    )


    # --------------------------------------------------
    # CREATE EMBEDDINGS
    # --------------------------------------------------

    embedded_chunks = embedder.embed_chunks(
        chunks
    )


    # --------------------------------------------------
    # SAVE EMBEDDINGS
    # --------------------------------------------------

    embedder.save_embeddings(
        embedded_chunks,
        output_path
    )


    print()
    print("=" * 60)
    print("DOCUMENT EMBEDDING COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Total Embedded Chunks: "
        f"{len(embedded_chunks)}"
    )


if __name__ == "__main__":

    main()