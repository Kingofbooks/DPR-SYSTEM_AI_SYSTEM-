import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from backend.config import PROCESSED_DATA_DIR, RAW_DATA_DIR, REGISTRY_PATH
from backend.utils.file_utils import safe_filename


class DocumentService:
    def __init__(self):
        self.registry_path = REGISTRY_PATH
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"documents": {}}
        with self.registry_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {"documents": {}}

    def _write_registry(self, data: dict[str, Any]) -> None:
        temporary_path = self.registry_path.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        temporary_path.replace(self.registry_path)

    def upload(self, upload: UploadFile) -> dict[str, Any]:
        filename = safe_filename(upload.filename or "document.pdf")
        if Path(filename).suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        document_id = str(uuid.uuid4())
        stored_name = f"{document_id}_{filename}"
        raw_path = RAW_DATA_DIR / stored_name
        content = upload.file.read()
        if not content or not content.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")
        raw_path.write_bytes(content)

        now = datetime.now(timezone.utc).isoformat()
        record = {
            "document_id": document_id,
            "filename": filename,
            "raw_path": str(raw_path),
            "processed_path": str(PROCESSED_DATA_DIR / document_id),
            "status": "uploaded",
            "created_at": now,
        }
        registry = self._read_registry()
        registry.setdefault("documents", {})[document_id] = record
        self._write_registry(registry)
        return record

    def get(self, document_id: str) -> dict[str, Any]:
        record = self._read_registry().get("documents", {}).get(document_id)
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")
        return record

    def list(self) -> list[dict[str, Any]]:
        return list(self._read_registry().get("documents", {}).values())

    def update_status(self, document_id: str, status: str) -> dict[str, Any]:
        registry = self._read_registry()
        record = registry.get("documents", {}).get(document_id)
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")
        record["status"] = status
        self._write_registry(registry)
        return record

    def analysis_path(self, document_id: str, analysis_name: str) -> Path:
        record = self.get(document_id)
        return Path(record["processed_path"]) / f"{analysis_name}.json"

    def load_analysis(self, document_id: str, analysis_name: str) -> dict[str, Any]:
        record = self.get(document_id)
        if record.get("status") != "processed":
            raise HTTPException(status_code=400, detail="Document has not been processed yet")
        path = self.analysis_path(document_id, analysis_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"{analysis_name} analysis not found")
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
