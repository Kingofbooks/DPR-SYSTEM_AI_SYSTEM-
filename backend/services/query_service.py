from pathlib import Path

from backend.services.document_service import DocumentService
from modules.generation.rag_generator import RAGGenerator


class QueryService:
    def __init__(self, documents: DocumentService | None = None):
        self.documents = documents or DocumentService()

    def ask(self, document_id: str, question: str, top_k: int = 5) -> dict:
        record = self.documents.get(document_id)
        if record.get("status") != "processed":
            raise ValueError("Document has not been processed yet")
        embeddings_path = Path(record["processed_path"]) / "embeddings.json"
        generator = RAGGenerator(top_k=top_k, embeddings_path=str(embeddings_path))
        result = generator.generate(question=question, top_k=top_k)
        return {
            "success": True,
            "document_id": document_id,
            "question": question,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
        }
