from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class SourceResponse(BaseModel):
    chunk_id: str = ""
    section_id: str = "Unknown"
    section_title: str = "Unknown"
    similarity: float = 0.0


class QueryResponse(BaseModel):
    success: bool
    document_id: str
    question: str
    answer: str
    sources: list[SourceResponse] = Field(default_factory=list)
