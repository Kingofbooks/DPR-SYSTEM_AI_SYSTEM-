import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ProcessResponse,
    ProcessResults,
)
from backend.services.document_service import DocumentService
from backend.services.pipeline_service import PipelineService

router = APIRouter(prefix="/documents", tags=["documents"])
documents = DocumentService()
pipeline = PipelineService()
logger = logging.getLogger(__name__)


def _document_response(record: dict) -> DocumentResponse:
    metadata = {}
    path = Path(record["processed_path"]) / "document.json"
    if path.exists():
        import json
        with path.open("r", encoding="utf-8") as file:
            metadata = json.load(file).get("metadata", {})
    return DocumentResponse(
        document_id=record["document_id"],
        filename=record["filename"],
        status=record["status"],
        metadata=metadata,
    )


@router.post("/upload", response_model=DocumentUploadResponse, description="Upload a DPR PDF.")
async def upload_document(file: UploadFile = File(...)):
    record = documents.upload(file)
    return DocumentUploadResponse(
        success=True,
        document_id=record["document_id"],
        filename=record["filename"],
        message="Document uploaded successfully",
    )


@router.post("/{document_id}/process", response_model=ProcessResponse, description="Run the complete DPR analysis pipeline.")
def process_document(document_id: str):
    record = documents.get(document_id)
    if record["status"] == "processing":
        raise HTTPException(status_code=409, detail="Document is already being processed")
    documents.update_status(document_id, "processing")
    try:
        result = pipeline.process_document(document_id, record["raw_path"], record["processed_path"])
        documents.update_status(document_id, "processed")
        completeness = result["completeness"].get("summary", {})
        quality = result["quality"].get("summary", {})
        risk = result["risk"].get("risk_assessment", {})
        return ProcessResponse(
            success=True,
            document_id=document_id,
            message="Document processed successfully",
            results=ProcessResults(
                sections=len(result["document"].get("sections", [])),
                chunks=len(result["chunks"]),
                completeness_score=float(completeness.get("overall_score", 0.0)),
                quality_score=float(quality.get("overall_quality", 0.0)),
                risk_score=float(risk.get("risk_score", 0.0)),
                risk_level=str(risk.get("risk_level", "UNKNOWN")),
            ),
        )
    except HTTPException:
        documents.update_status(document_id, "failed")
        raise
    except Exception as error:
        documents.update_status(document_id, "failed")
        logger.exception("Pipeline failed for document %s", document_id)
        raise HTTPException(status_code=500, detail="Document processing failed") from error


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str):
    return _document_response(documents.get(document_id))


@router.get("", response_model=DocumentListResponse)
def list_documents():
    return DocumentListResponse(documents=[_document_response(record) for record in documents.list()])
