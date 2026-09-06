from fastapi import APIRouter

from backend.schemas.analysis import (
    CompleteAnalysisResponse,
    CompletenessResponse,
    FeaturesResponse,
    QualityResponse,
    RiskResponse,
)
from backend.services.document_service import DocumentService

router = APIRouter(prefix="/analysis", tags=["analysis"])
documents = DocumentService()


@router.get("/{document_id}/completeness", response_model=CompletenessResponse)
def completeness(document_id: str):
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "completeness")}


@router.get("/{document_id}/quality", response_model=QualityResponse)
def quality(document_id: str):
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "quality")}


@router.get("/{document_id}/features", response_model=FeaturesResponse)
def features(document_id: str):
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "features")}


@router.get("/{document_id}/risk", response_model=RiskResponse)
def risk(document_id: str):
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "risk")}


@router.get("/{document_id}", response_model=CompleteAnalysisResponse)
def complete_analysis(document_id: str):
    return {
        "document_id": document_id,
        "completeness": documents.load_analysis(document_id, "completeness"),
        "quality": documents.load_analysis(document_id, "quality"),
        "features": documents.load_analysis(document_id, "features"),
        "risk": documents.load_analysis(document_id, "risk"),
    }
