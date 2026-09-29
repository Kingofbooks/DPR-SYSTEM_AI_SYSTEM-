from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import PROCESSED_DATA_DIR, RAW_DATA_DIR, REGISTRY_PATH
from backend.db.database import SessionLocal
from backend.db.models import DPRAssessment, DPRDocument
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

    def _sync_db_document(self, record: dict[str, Any]) -> None:
        db: Session = SessionLocal()
        try:
            document = db.get(DPRDocument, record["document_id"])
            payload = {
                "id": record["document_id"],
                "user_id": record.get("user_id"),
                "original_filename": record.get("filename", "document.pdf"),
                "stored_path": record.get("raw_path", str(RAW_DATA_DIR / f"{record['document_id']}.pdf")),
                "processing_status": record.get("status", "uploaded"),
            }
            if document is None:
                db.add(DPRDocument(**payload))
            else:
                document.user_id = payload["user_id"]
                document.original_filename = payload["original_filename"]
                document.stored_path = payload["stored_path"]
                document.processing_status = payload["processing_status"]
            db.commit()
        finally:
            db.close()

    def upload(self, upload: UploadFile, user_id: str | None = None) -> dict[str, Any]:
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
            "user_id": user_id,
        }
        registry = self._read_registry()
        registry.setdefault("documents", {})[document_id] = record
        self._write_registry(registry)
        self._sync_db_document(record)
        return record

    def get(self, document_id: str) -> dict[str, Any]:
        record = self._read_registry().get("documents", {}).get(document_id)
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")
        return record

    def get_for_user(self, document_id: str, user_id: str) -> dict[str, Any]:
        record = self.get(document_id)
        if record.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Document not found")
        return record

    def list(self) -> list[dict[str, Any]]:
        return list(self._read_registry().get("documents", {}).values())

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [record for record in self.list() if record.get("user_id") == user_id]

    def update_status(self, document_id: str, status: str) -> dict[str, Any]:
        registry = self._read_registry()
        record = registry.get("documents", {}).get(document_id)
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")
        record["status"] = status
        self._write_registry(registry)
        self._sync_db_document(record)
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

    def save_assessment_for_document(self, document_id: str, assessment_payload: dict[str, Any]) -> DPRAssessment:
        if not isinstance(assessment_payload, dict):
            raise HTTPException(status_code=400, detail="Invalid assessment payload")

        completeness = assessment_payload.get("completeness", {}) if isinstance(assessment_payload.get("completeness"), dict) else {}
        quality = assessment_payload.get("quality", {}) if isinstance(assessment_payload.get("quality"), dict) else {}
        risk = assessment_payload.get("risk", {}) if isinstance(assessment_payload.get("risk"), dict) else {}
        risk_assessment = risk.get("risk_assessment", {}) if isinstance(risk, dict) else {}

        db: Session = SessionLocal()
        try:
            document = db.scalar(select(DPRDocument).where(DPRDocument.id == document_id))
            if document is None:
                registry_record = self.get(document_id)
                if registry_record:
                    self._sync_db_document(registry_record)
                    document = db.scalar(select(DPRDocument).where(DPRDocument.id == document_id))
            if document is None:
                raise HTTPException(status_code=404, detail="Document not found")

            record = DPRAssessment(
                document_id=document_id,
                completeness_score=_coerce_float(completeness.get("summary", {}).get("overall_score"), completeness.get("overall_score")),
                quality_score=_coerce_float(quality.get("summary", {}).get("overall_quality"), quality.get("overall_quality")),
                risk_score=_coerce_float(risk_assessment.get("risk_score"), risk.get("risk_score")),
                risk_percentage=_coerce_float(risk_assessment.get("risk_percentage"), risk.get("risk_percentage")),
                risk_level=str(risk_assessment.get("risk_level") or risk.get("risk_level") or "UNKNOWN"),
                structured_assessment_json=json.dumps(assessment_payload, ensure_ascii=False),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record
        finally:
            db.close()

    def get_latest_assessment_for_document(self, document_id: str, user_id: str) -> DPRAssessment | None:
        db: Session = SessionLocal()
        try:
            document = db.scalar(select(DPRDocument).where(DPRDocument.id == document_id))
            if document is None or document.user_id != user_id:
                return None
            return db.scalar(
                select(DPRAssessment)
                .where(DPRAssessment.document_id == document_id)
                .order_by(DPRAssessment.created_at.desc())
            )
        finally:
            db.close()

    def list_assessments_for_document(self, document_id: str, user_id: str) -> list[dict[str, Any]]:
        db: Session = SessionLocal()
        try:
            document = db.scalar(select(DPRDocument).where(DPRDocument.id == document_id))
            if document is None or document.user_id != user_id:
                return []
            assessments = db.scalars(
                select(DPRAssessment)
                .where(DPRAssessment.document_id == document_id)
                .order_by(DPRAssessment.created_at.desc())
            ).all()
            return [
                {
                    "id": assessment.id,
                    "completeness_score": assessment.completeness_score,
                    "quality_score": assessment.quality_score,
                    "risk_score": assessment.risk_score,
                    "risk_percentage": assessment.risk_percentage,
                    "risk_level": assessment.risk_level,
                    "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                }
                for assessment in assessments
            ]
        finally:
            db.close()


def _coerce_float(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
