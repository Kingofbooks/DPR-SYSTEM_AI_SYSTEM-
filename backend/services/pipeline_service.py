import json
from pathlib import Path

from modules.analysis.completeness_checker import CompletenessChecker
from modules.analysis.feature_constructor import FeatureConstructor
from modules.analysis.quality_checker import QualityAssessor
from modules.analysis.risk_scorer import RiskScorer
from modules.classification.section_classifier import SectionClassifier
from modules.processing.document_processor import DocumentProcessor
from modules.retrieval.chunker import DocumentChunker
from modules.retrieval.embedder import DocumentEmbedder


class PipelineService:
    """Orchestrates the existing DPR pipeline for one document."""

    def process_document(self, document_id: str, pdf_path: str | Path, output_dir: str | Path):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = Path(pdf_path)

        document_path = output_dir / "document.json"
        chunks_path = output_dir / "chunks.json"
        embeddings_path = output_dir / "embeddings.json"
        completeness_path = output_dir / "completeness.json"
        quality_path = output_dir / "quality.json"
        features_path = output_dir / "features.json"
        risk_path = output_dir / "risk.json"

        document_processor = DocumentProcessor()
        document = document_processor.process(pdf_path)
        document_processor.save_json(document, document_path)

        chunks = DocumentChunker().process(document_path, chunks_path)
        embedder = DocumentEmbedder()
        embedded_chunks = embedder.embed_chunks(chunks)
        embedder.save_embeddings(embedded_chunks, embeddings_path)

        classified = SectionClassifier().classify_sections(document)
        completeness_checker = CompletenessChecker()
        completeness = completeness_checker.validate_with_llm(
            completeness_checker.check_completeness(classified)
        )
        quality = QualityAssessor().assess_quality(classified)

        self._save_json(completeness_path, completeness)
        self._save_json(quality_path, quality)
        features = FeatureConstructor().construct_features(completeness_path, quality_path)
        risk = RiskScorer().assess(features)

        self._save_json(features_path, features)
        self._save_json(risk_path, risk)

        return {
            "document": document,
            "classified": classified,
            "chunks": chunks,
            "completeness": completeness,
            "quality": quality,
            "features": features,
            "risk": risk,
            "paths": {
                "document": document_path,
                "chunks": chunks_path,
                "embeddings": embeddings_path,
                "completeness": completeness_path,
                "quality": quality_path,
                "features": features_path,
                "risk": risk_path,
            },
        }

    @staticmethod
    def _save_json(path: Path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(value, file, indent=2, ensure_ascii=False)


def run_pipeline(pdf_path=None):
    """Backward-compatible entry point for the previous backend stub."""
    from backend.config import PROCESSED_DATA_DIR

    result = PipelineService().process_document("legacy", pdf_path, PROCESSED_DATA_DIR / "legacy")
    return {key: result[key] for key in ("classified", "completeness", "quality", "features", "risk")}
