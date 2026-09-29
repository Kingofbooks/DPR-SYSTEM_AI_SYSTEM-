from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"


def ensure_document_storage(document_id: str) -> dict[str, Path]:
    if not document_id or not str(document_id).strip():
        raise ValueError("Document ID is required for storage")

    document_id = str(document_id).strip()
    upload_dir = UPLOADS_DIR / document_id
    processed_dir = PROCESSED_DIR / document_id

    upload_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    return {
        "upload_dir": upload_dir,
        "processed_dir": processed_dir,
    }


def build_safe_filename(filename: str) -> str:
    candidate = (filename or "document.pdf").strip()
    name = Path(candidate).name or "document.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{Path(name).stem}.pdf"
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in {".", "_", "-"})
    return safe_name or "document.pdf"


def get_document_upload_path(document_id: str, filename: str) -> Path:
    storage = ensure_document_storage(document_id)
    return storage["upload_dir"] / build_safe_filename(filename)


def get_document_processed_path(document_id: str) -> Path:
    storage = ensure_document_storage(document_id)
    return storage["processed_dir"]
