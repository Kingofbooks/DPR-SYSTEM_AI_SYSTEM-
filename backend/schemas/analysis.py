from typing import Any

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    document_id: str
    data: dict[str, Any]


class CompletenessResponse(AnalysisResponse):
    pass


class QualityResponse(AnalysisResponse):
    pass


class FeaturesResponse(AnalysisResponse):
    pass


class RiskResponse(AnalysisResponse):
    pass


class AssessmentHistoryEntry(BaseModel):
    id: str
    completeness_score: float | None = None
    quality_score: float | None = None
    risk_score: float | None = None
    risk_percentage: float | None = None
    risk_level: str | None = None
    created_at: str | None = None


class AssessmentHistoryResponse(BaseModel):
    document_id: str
    assessments: list[AssessmentHistoryEntry]


class CompleteAnalysisResponse(BaseModel):
    document_id: str
    completeness: dict[str, Any]
    quality: dict[str, Any]
    features: dict[str, Any]
    risk: dict[str, Any]
