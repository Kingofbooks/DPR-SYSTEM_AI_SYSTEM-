from pathlib import Path
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException

from pipeline.pipeline import run_pipeline


app = FastAPI(
    title="DPR AI Analysis Service",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "dpr-ai"
    }


@app.post("/api/analyze")
async def analyze_dpr(file: UploadFile = File(...)):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    try:
        # Create temporary PDF
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            content = await file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        # Run existing AI pipeline
        result = run_pipeline(temp_path)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DPR analysis failed: {str(e)}"
        )

    finally:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()