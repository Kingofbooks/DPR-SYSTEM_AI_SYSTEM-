from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.analysis import router as analysis_router
from backend.routes.documents import router as documents_router
from backend.routes.query import router as query_router

app = FastAPI(
    title="DPR AI System API",
    description="API for processing and querying Detailed Project Reports.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "healthy", "service": "DPR AI System"}


app.include_router(documents_router)
app.include_router(query_router)
app.include_router(analysis_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
