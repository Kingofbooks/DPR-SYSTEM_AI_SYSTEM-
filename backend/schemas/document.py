from typing import Any

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str
    filename: str
    message: str


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class ProcessResults(BaseModel):
    sections: int
    chunks: int
    completeness_score: float
    quality_score: float
    risk_score: float
    risk_level: str


class ProcessResponse(BaseModel):
    success: bool
    document_id: str
    message: str
    results: ProcessResults
