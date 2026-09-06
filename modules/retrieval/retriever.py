import json
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer


class DocumentRetriever:
    """
    Retrieves the most relevant document chunks
    using cosine similarity between embeddings.
    """

    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        embeddings_path: str = "data/processed/DPR of Road_embeddings.json",
    ):
        print("Document Retriever initialized.")

        self.embedding_model_name = embedding_model_name
        self.embeddings_path = Path(embeddings_path)

        self.model = None
        self.embedded_chunks: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # LOAD EMBEDDING MODEL
    # --------------------------------------------------

    def load_model(self):
        """
        Load the same embedding model used
        during document embedding.
        """

        if self.model is None:
            print(
                f"Loading embedding model: "
                f"{self.embedding_model_name}"
            )

            self.model = SentenceTransformer(
                self.embedding_model_name
            )

            print("Embedding model loaded successfully.")

    # --------------------------------------------------
    # LOAD EMBEDDINGS
    # --------------------------------------------------

    def load_embeddings(self):
        """
        Load embedded document chunks from JSON.
        """

        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"Embeddings file not found:\n"
                f"{self.embeddings_path}"
            )

        print("\nLoading embeddings...")

        with open(
            self.embeddings_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        # Handle possible JSON structures safely
        if isinstance(data, dict):

            if "embedded_chunks" in data:
                self.embedded_chunks = data[
                    "embedded_chunks"
                ]

            elif "chunks" in data:
                self.embedded_chunks = data[
                    "chunks"
                ]

            else:
                raise ValueError(
                    "Could not find embedded chunks in JSON."
                )

        elif isinstance(data, list):
            self.embedded_chunks = data

        else:
            raise ValueError(
                "Invalid embeddings file format."
            )

        print(
            f"Embedded chunks loaded: "
            f"{len(self.embedded_chunks)}"
        )

    # --------------------------------------------------
    # COSINE SIMILARITY
    # --------------------------------------------------

    @staticmethod
    def cosine_similarity(
        vector_a: np.ndarray,
        vector_b: np.ndarray,
    ) -> float:
        """
        Calculate cosine similarity between
        two vectors.
        """

        denominator = (
            np.linalg.norm(vector_a)
            * np.linalg.norm(vector_b)
        )

        if denominator == 0:
            return 0.0

        return float(
            np.dot(vector_a, vector_b)
            / denominator
        )

    # --------------------------------------------------
    # RETRIEVE
    # --------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top_k most relevant chunks
        for a user query.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # Load model if needed
        self.load_model()

        # Load embeddings if needed
        if not self.embedded_chunks:
            self.load_embeddings()

        print("\nGenerating query embedding...")

        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True,
        )

        print("Searching for relevant chunks...")

        results = []

        for chunk in self.embedded_chunks:

            embedding = chunk.get("embedding")

            if embedding is None:
                continue

            chunk_embedding = np.array(
                embedding,
                dtype=np.float32,
            )

            similarity = self.cosine_similarity(
                query_embedding,
                chunk_embedding,
            )

            result = {
                "chunk_id": chunk.get(
                    "chunk_id",
                    "unknown",
                ),
                "section_id": chunk.get(
                    "section_id",
                    "unknown",
                ),
                "section_title": chunk.get(
                    "section_title",
                    chunk.get("title", "Unknown"),
                ),
                "chunk_index": chunk.get(
                    "chunk_index",
                    0,
                ),
                "content": chunk.get(
                    "content",
                    "",
                ),
                "similarity": similarity,
            }

            results.append(result)

        # Sort by similarity
        results.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        return results[:top_k]


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("STARTING DOCUMENT RETRIEVAL")
    print("=" * 60)

    retriever = DocumentRetriever()

    # ------------------------------------------------------
    # TEST QUERY
    # ------------------------------------------------------

    query = "What is the proposed road alignment?"

    print("\nQuery:")
    print(query)

    # ------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------

    results = retriever.retrieve(
        query=query,
        top_k=5,
    )

    # ------------------------------------------------------
    # DISPLAY RESULTS
    # ------------------------------------------------------

    print("\n" + "=" * 60)
    print("RETRIEVAL RESULTS")
    print("=" * 60)

    print(f"\nResults found: {len(results)}")

    for index, result in enumerate(
        results,
        start=1,
    ):

        print("\n" + "-" * 60)

        print(f"RESULT #{index}")

        print(
            f"Chunk ID: "
            f"{result['chunk_id']}"
        )

        print(
            f"Section ID: "
            f"{result['section_id']}"
        )

        print(
            f"Section Title: "
            f"{result['section_title']}"
        )

        print(
            f"Similarity Score: "
            f"{result['similarity']:.4f}"
        )

        print("\nCONTENT:")

        content = result["content"]

        # Print only preview
        if len(content) > 800:
            print(content[:800])
            print("\n[Content truncated...]")
        else:
            print(content)

    print("\n" + "=" * 60)
    print("DOCUMENT RETRIEVAL COMPLETE")
    print("=" * 60)