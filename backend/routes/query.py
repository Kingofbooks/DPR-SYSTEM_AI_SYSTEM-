import logging

from fastapi import APIRouter, HTTPException

from backend.schemas.query import QueryRequest, QueryResponse
from backend.services.query_service import QueryService

router = APIRouter(tags=["query"])
service = QueryService()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse, description="Ask a question about one processed DPR.")
def ask_question(request: QueryRequest):
    try:
        return service.ask(request.document_id, request.question.strip(), request.top_k)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Query failed for document %s", request.document_id)
        raise HTTPException(status_code=500, detail="Query processing failed") from error
