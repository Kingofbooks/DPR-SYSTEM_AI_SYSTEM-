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


class CompleteAnalysisResponse(BaseModel):
    document_id: str
    completeness: dict[str, Any]
    quality: dict[str, Any]
    features: dict[str, Any]
    risk: dict[str, Any]
