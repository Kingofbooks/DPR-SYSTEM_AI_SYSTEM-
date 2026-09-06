"""Application-facing pipeline routes."""

from pathlib import Path

from backend.services.pipeline_service import run_pipeline


def analyze_document(pdf_path: str | Path | None = None):
    """Run the DPR analysis pipeline for a PDF document."""
    return run_pipeline(pdf_path)