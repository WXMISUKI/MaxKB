from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from .config import Settings
from .schemas import IngestKnowledgeRequest, RetrievalCheckRequest


class ProviderAdapters:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        scripts_path = settings.project_root / "docs" / "construction-supervision-local-validation" / "scripts"
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))

    def ocr_and_archive(
        self,
        source: str,
        model: str,
        optional_payload: dict[str, bool],
        on_submitted: Callable[[str], None],
    ) -> dict[str, Any]:
        from paddleocr_vl_ingest import PaddleOcrClient, archive_ocr_result

        if not self.settings.paddleocr_token:
            raise RuntimeError("PaddleOCR provider is not configured.")
        client = PaddleOcrClient(
            self.settings.paddleocr_job_url,
            self.settings.paddleocr_token,
            model or self.settings.paddleocr_model,
            poll_interval=5,
            timeout_seconds=1800,
        )
        job_id = client.submit(source, optional_payload)
        on_submitted(job_id)
        data = client.poll(job_id)
        artifact = archive_ocr_result(source, job_id, data)
        return {
            "provider_job_id": job_id,
            "raw_ocr_markdown_path": str(artifact.combined_markdown),
            "ocr_output_dir": str(artifact.output_dir),
            "page_count": artifact.page_count,
        }

    def postprocess(
        self,
        source_markdown: str,
        certificate_type: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        from postprocess_ocr_document import postprocess

        script_metadata = {
            "organization_id": metadata.get("organization_id", ""),
            "project_id": metadata.get("project_id", ""),
            "project_name": metadata.get("project_name", ""),
            "contract_package_id": metadata.get("contract_package_id", ""),
            "team_id": metadata.get("team_id", ""),
            "team_name": metadata.get("team_name", ""),
            "review_task_id": metadata.get("review_task_id", ""),
            "document_type": metadata.get("document_type", ""),
            "source_object_type": metadata.get("source_object_type", ""),
            "source_file_path": metadata.get("source_file_path", ""),
            "source_object_id": metadata.get("source_object_id", ""),
            "content_hash": metadata.get("content_hash", ""),
        }
        artifact = postprocess(Path(source_markdown), certificate_type, script_metadata)
        return {
            "certificate_type": artifact.certificate_type,
            "fields": artifact.extracted_fields,
            "warnings": artifact.warnings,
            "artifacts": {
                "cleaned_markdown_path": str(artifact.cleaned_markdown),
                "fields_json_path": str(artifact.fields_json),
                "fields_csv_path": str(artifact.fields_csv),
                "ingest_markdown_path": str(artifact.ingest_markdown),
                "report_markdown_path": str(artifact.report_markdown),
            },
        }

    def ingest_to_maxkb(
        self,
        ingest_markdown_path: str,
        request: IngestKnowledgeRequest,
    ) -> dict[str, Any]:
        from configure_and_upload_maxkb import MaxKBClient, MaxKBError

        client = MaxKBClient(self.settings.maxkb_base_url)
        client.login(self.settings.maxkb_username, self.settings.maxkb_password)
        workspace_id = request.workspace_id or self.settings.maxkb_workspace_id
        knowledge = None
        for item in client.list_knowledge(workspace_id):
            if request.knowledge_base_id and item.get("id") == request.knowledge_base_id:
                knowledge = item
                break
            target_name = request.knowledge_name or self.settings.maxkb_knowledge_name
            if not request.knowledge_base_id and item.get("name") == target_name:
                knowledge = item
                break
        if not knowledge:
            raise MaxKBError("Configured MaxKB knowledge base was not found.")
        result = client.upload_text_document(workspace_id, knowledge["id"], Path(ingest_markdown_path))
        document = result[0] if isinstance(result, list) and result else {}
        return {
            "provider": "maxkb",
            "workspace_id": workspace_id,
            "knowledge_base_id": knowledge["id"],
            "provider_document_id": document.get("id", ""),
            "provider_document_name": Path(ingest_markdown_path).name,
        }

    def retrieval_check(
        self,
        provider_refs: dict[str, Any],
        request: RetrievalCheckRequest,
    ) -> dict[str, Any]:
        from configure_and_upload_maxkb import MaxKBClient

        client = MaxKBClient(self.settings.maxkb_base_url)
        client.login(self.settings.maxkb_username, self.settings.maxkb_password)
        workspace_id = provider_refs["workspace_id"]
        knowledge_id = provider_refs["knowledge_base_id"]
        rows = []
        for query in request.queries:
            hits = client.request(
                "POST",
                f"/workspace/{workspace_id}/knowledge/{knowledge_id}/hit_test",
                json={
                    "query_text": query,
                    "top_number": request.top_number,
                    "similarity": request.similarity,
                    "search_mode": request.search_mode,
                },
            ) or []
            matched = next(
                (hit for hit in hits if self._document_name(hit) == request.expected_document_name),
                None,
            )
            top = hits[0] if hits else {}
            rows.append(
                {
                    "query": query,
                    "classification": "pass" if matched else "fail",
                    "expected_rank": hits.index(matched) + 1 if matched else None,
                    "expected_similarity": matched.get("similarity") if matched else None,
                    "top_document": self._document_name(top),
                    "top_similarity": top.get("similarity"),
                }
            )
        return {
            "pass": sum(1 for item in rows if item["classification"] == "pass"),
            "fail": sum(1 for item in rows if item["classification"] == "fail"),
            "results": rows,
        }

    @staticmethod
    def _document_name(hit: dict[str, Any]) -> str:
        return str(hit.get("document_name") or hit.get("document", {}).get("name") or "")

