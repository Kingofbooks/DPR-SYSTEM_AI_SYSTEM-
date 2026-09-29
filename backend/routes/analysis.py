import json

from fastapi import APIRouter, Depends

from backend.db.models import User
from backend.schemas.analysis import (
    AssessmentHistoryResponse,
    CompleteAnalysisResponse,
    CompletenessResponse,
    FeaturesResponse,
    QualityResponse,
    RiskResponse,
)
from backend.security import get_current_user
from backend.services.document_service import DocumentService

router = APIRouter(prefix="/analysis", tags=["analysis"])
documents = DocumentService()


def _db_assessment_payload(document_id: str, user_id: str):
    assessment = documents.get_latest_assessment_for_document(document_id, user_id)
    if assessment is None or not assessment.structured_assessment_json:
        return None
    try:
        return json.loads(assessment.structured_assessment_json)
    except json.JSONDecodeError:
        return None


@router.get("/{document_id}/completeness", response_model=CompletenessResponse)
def completeness(document_id: str, current_user: User = Depends(get_current_user)):
    documents.get_for_user(document_id, current_user.id)
    db_assessment = _db_assessment_payload(document_id, current_user.id)
    if db_assessment is not None and "completeness" in db_assessment:
        return {"document_id": document_id, "data": db_assessment["completeness"]}
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "completeness")}


@router.get("/{document_id}/quality", response_model=QualityResponse)
def quality(document_id: str, current_user: User = Depends(get_current_user)):
    documents.get_for_user(document_id, current_user.id)
    db_assessment = _db_assessment_payload(document_id, current_user.id)
    if db_assessment is not None and "quality" in db_assessment:
        return {"document_id": document_id, "data": db_assessment["quality"]}
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "quality")}


@router.get("/{document_id}/features", response_model=FeaturesResponse)
def features(document_id: str, current_user: User = Depends(get_current_user)):
    documents.get_for_user(document_id, current_user.id)
    db_assessment = _db_assessment_payload(document_id, current_user.id)
    if db_assessment is not None and "features" in db_assessment:
        return {"document_id": document_id, "data": db_assessment["features"]}
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "features")}


@router.get("/{document_id}/risk", response_model=RiskResponse)
def risk(document_id: str, current_user: User = Depends(get_current_user)):
    documents.get_for_user(document_id, current_user.id)
    db_assessment = _db_assessment_payload(document_id, current_user.id)
    if db_assessment is not None and "risk" in db_assessment:
        return {"document_id": document_id, "data": db_assessment["risk"]}
    return {"document_id": document_id, "data": documents.load_analysis(document_id, "risk")}


@router.get("/{document_id}/history", response_model=AssessmentHistoryResponse)
def assessment_history(document_id: str, current_user: User = Depends(get_current_user)):
    documents.get_for_user(document_id, current_user.id)
    return {
        "document_id": document_id,
        "assessments": documents.list_assessments_for_document(document_id, current_user.id),
    }


@router.get("/{document_id}", response_model=CompleteAnalysisResponse)
def complete_analysis(document_id: str, current_user: User = Depends(get_current_user)):
    documents.get_for_user(document_id, current_user.id)
    db_assessment = _db_assessment_payload(document_id, current_user.id)
    if db_assessment is not None:
        return {
            "document_id": document_id,
            "completeness": db_assessment.get("completeness", documents.load_analysis(document_id, "completeness")),
            "quality": db_assessment.get("quality", documents.load_analysis(document_id, "quality")),
            "features": db_assessment.get("features", documents.load_analysis(document_id, "features")),
            "risk": db_assessment.get("risk", documents.load_analysis(document_id, "risk")),
        }
    return {
        "document_id": document_id,
        "completeness": documents.load_analysis(document_id, "completeness"),
        "quality": documents.load_analysis(document_id, "quality"),
        "features": documents.load_analysis(document_id, "features"),
        "risk": documents.load_analysis(document_id, "risk"),
    }
