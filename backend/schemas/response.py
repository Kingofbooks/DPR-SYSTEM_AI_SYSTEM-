"""Shared response shape for document analysis results."""

from typing import Any, TypedDict


class AnalysisResponse(TypedDict):
    classified_sections: Any
    completeness: Any
    quality: Any
    features: Any
    risk: Any