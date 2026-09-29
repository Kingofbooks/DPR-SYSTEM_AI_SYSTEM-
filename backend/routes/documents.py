import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.db.models import User
from backend.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ProcessResponse,
    ProcessResults,
)
from backend.security import get_current_user
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
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    record = documents.upload(file, user_id=current_user.id)
    return DocumentUploadResponse(
        success=True,
        document_id=record["document_id"],
        filename=record["filename"],
        message="Document uploaded successfully",
    )


def _run_background_processing(document_id: str, user_id: str) -> None:
    try:
        record = documents.get_for_user(document_id, user_id)
        result = pipeline.process_document(document_id, record["raw_path"], record["processed_path"])
        documents.update_status(document_id, "processed")
        completeness = result["completeness"].get("summary", {})
        quality = result["quality"].get("summary", {})
        risk = result["risk"].get("risk_assessment", {})

        assessment_payload = {
            "document_id": document_id,
            "completeness": result.get("completeness", {}),
            "quality": result.get("quality", {}),
            "features": result.get("features", {}),
            "risk": result.get("risk", {}),
        }
        documents.save_assessment_for_document(document_id, assessment_payload)
        logger.info("Background processing completed for document %s", document_id)
    except HTTPException:
        documents.update_status(document_id, "failed")
        logger.warning("Processing failed for document %s because the document is not available", document_id)
    except Exception as error:
        documents.update_status(document_id, "failed")
        logger.exception("Pipeline failed for document %s", document_id)
        raise RuntimeError("Document processing failed") from error


@router.post("/{document_id}/process", response_model=ProcessResponse, description="Run the complete DPR analysis pipeline in the background.")
async def process_document(document_id: str, current_user: User = Depends(get_current_user)):
    record = documents.get_for_user(document_id, current_user.id)
    if record["status"] == "processing":
        raise HTTPException(status_code=409, detail="Document is already being processed")
    documents.update_status(document_id, "processing")

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_background_processing, document_id, current_user.id)

    return ProcessResponse(
        success=True,
        document_id=document_id,
        message="Document processing started in the background",
        results=ProcessResults(
            sections=0,
            chunks=0,
            completeness_score=0.0,
            quality_score=0.0,
            risk_score=0.0,
            risk_level="PROCESSING",
        ),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, current_user: User = Depends(get_current_user)):
    return _document_response(documents.get_for_user(document_id, current_user.id))


@router.get("", response_model=DocumentListResponse)
def list_documents(current_user: User = Depends(get_current_user)):
    return DocumentListResponse(documents=[_document_response(record) for record in documents.list_for_user(current_user.id)])
