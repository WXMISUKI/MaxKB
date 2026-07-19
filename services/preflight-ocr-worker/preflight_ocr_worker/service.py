from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .adapters import ProviderAdapters
from .config import Settings
from .schemas import (
    CreateIngestionRequest,
    IngestKnowledgeRequest,
    PostprocessRequest,
    RetrievalCheckRequest,
)
from .store import JsonStateStore


class IngestionService:
    def __init__(self, settings: Settings, store: JsonStateStore, adapters: ProviderAdapters) -> None:
        self.settings = settings
        self.store = store
        self.adapters = adapters

    def create(self, request: CreateIngestionRequest) -> dict[str, Any]:
        source = self._validated_source(request)
        now = self._now()
        record = {
            "ingestion_id": f"ocring_{uuid4().hex}",
            "correlation_id": f"corr_{uuid4().hex}",
            "status": "registered",
            "metadata": request.metadata.model_dump(),
            "source": request.source.model_dump(),
            "resolved_source": source,
            "ocr": request.ocr.model_dump(),
            "artifacts": {},
            "postprocess": {},
            "provider_refs": {},
            "retrieval_check": {},
            "error": None,
            "history": [{"status": "registered", "at": now}],
            "created_at": now,
            "updated_at": now,
        }
        return self.store.create(record)

    def get(self, ingestion_id: str) -> dict[str, Any] | None:
        return self.store.get(ingestion_id)

    def run_ocr_pipeline(self, ingestion_id: str) -> dict[str, Any]:
        try:
            record = self._require(ingestion_id)
            if record["status"] != "ocr_pending":
                record = self._transition(ingestion_id, "ocr_pending")

            def on_submitted(job_id: str) -> None:
                self._transition(ingestion_id, "ocr_running", {"provider_job_id": job_id})

            ocr_result = self.adapters.ocr_and_archive(
                record["resolved_source"],
                record["ocr"].get("model", ""),
                record["ocr"].get("optional_payload", {}),
                on_submitted,
            )
            self._transition(ingestion_id, "ocr_done", {"artifacts": ocr_result})
            return self.run_postprocess(ingestion_id, PostprocessRequest())
        except Exception as error:
            return self._fail(ingestion_id, "ocr_pipeline_error", error)

    def run_postprocess(self, ingestion_id: str, request: PostprocessRequest) -> dict[str, Any]:
        try:
            record = self._require(ingestion_id)
            source_markdown = record.get("artifacts", {}).get("raw_ocr_markdown_path")
            if not source_markdown:
                raise RuntimeError("OCR markdown artifact is not available.")
            result = self.adapters.postprocess(source_markdown, request.certificate_type, record["metadata"])
            self._transition(ingestion_id, "postprocessed", {"postprocess": result})
            return self._transition(ingestion_id, "ready_for_ingest")
        except Exception as error:
            return self._fail(ingestion_id, "postprocess_error", error)

    def ingest_to_knowledge(
        self,
        ingestion_id: str,
        request: IngestKnowledgeRequest,
    ) -> dict[str, Any]:
        try:
            record = self._require(ingestion_id)
            postprocess = record.get("postprocess", {})
            warnings = postprocess.get("warnings", [])
            if warnings and not request.confirm_postprocess_warnings:
                raise RuntimeError("Postprocess warnings must be confirmed before ingestion.")
            ingest_path = postprocess.get("artifacts", {}).get("ingest_markdown_path")
            if not ingest_path:
                raise RuntimeError("Certificate ingestion markdown is not available.")
            provider_refs = self.adapters.ingest_to_maxkb(ingest_path, request)
            return self._transition(ingestion_id, "ingested", {"provider_refs": provider_refs})
        except Exception as error:
            return self._fail(ingestion_id, "maxkb_ingestion_error", error)

    def retrieval_check(
        self,
        ingestion_id: str,
        request: RetrievalCheckRequest,
    ) -> dict[str, Any]:
        try:
            record = self._require(ingestion_id)
            if not record.get("provider_refs"):
                raise RuntimeError("MaxKB provider refs are not available.")
            result = self.adapters.retrieval_check(record["provider_refs"], request)
            return self._transition(ingestion_id, "retrieval_checked", {"retrieval_check": result})
        except Exception as error:
            return self._fail(ingestion_id, "retrieval_check_error", error)

    def _validated_source(self, request: CreateIngestionRequest) -> str:
        if request.source.mode == "url":
            return request.source.url
        path = Path(request.source.path)
        if not path.exists() or not path.is_file():
            raise ValueError("Local source file does not exist.")
        if not self.settings.is_allowed_source(path):
            raise PermissionError("Local source file is outside configured allowed roots.")
        return str(path.resolve())

    def _require(self, ingestion_id: str) -> dict[str, Any]:
        record = self.store.get(ingestion_id)
        if not record:
            raise KeyError(ingestion_id)
        return record

    def _transition(
        self,
        ingestion_id: str,
        status: str,
        values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._require(ingestion_id)
        now = self._now()
        history = [*record.get("history", []), {"status": status, "at": now}]
        update_values = {
            **(values or {}),
            "status": status,
            "history": history,
            "updated_at": now,
        }
        if status != "failed":
            update_values["error"] = None
        return self.store.update(
            ingestion_id,
            update_values,
        )

    def _fail(self, ingestion_id: str, error_type: str, error: Exception) -> dict[str, Any]:
        summary = str(error)[:500] or error.__class__.__name__
        try:
            return self._transition(
                ingestion_id,
                "failed",
                {
                    "error": {
                        "type": error_type,
                        "summary": summary,
                        "safe_diagnostics": {"exception_type": error.__class__.__name__},
                    }
                },
            )
        except KeyError:
            raise error

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
