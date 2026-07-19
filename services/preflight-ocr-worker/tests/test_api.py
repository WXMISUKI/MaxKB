from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient

from preflight_ocr_worker.config import Settings
from preflight_ocr_worker.main import create_app
from preflight_ocr_worker.store import JsonStateStore


class FakeAdapters:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ocr_calls = 0
        self.postprocess_metadata: dict[str, Any] = {}

    def ocr_and_archive(
        self,
        source: str,
        model: str,
        optional_payload: dict[str, bool],
        on_submitted: Callable[[str], None],
    ) -> dict[str, Any]:
        self.ocr_calls += 1
        on_submitted("job-test-001")
        markdown = self.root / "ocr.md"
        markdown.write_text("# 营业执照\n统一社会信用代码\n91310115515002x94", encoding="utf-8")
        return {
            "provider_job_id": "job-test-001",
            "raw_ocr_markdown_path": str(markdown),
            "ocr_output_dir": str(self.root),
            "page_count": 1,
        }

    def postprocess(
        self,
        source_markdown: str,
        certificate_type: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        self.postprocess_metadata = metadata
        ingest = self.root / "business-license-ingest.md"
        ingest.write_text("# 营业执照 OCR 结构化结果", encoding="utf-8")
        return {
            "certificate_type": "business_license",
            "fields": {"unified_social_credit_code": "91310115515002x94"},
            "warnings": [],
            "artifacts": {"ingest_markdown_path": str(ingest)},
        }

    def ingest_to_maxkb(self, ingest_markdown_path: str, request: Any) -> dict[str, Any]:
        return {
            "provider": "maxkb",
            "workspace_id": "default",
            "knowledge_base_id": "kb-test",
            "provider_document_id": "doc-test",
            "provider_document_name": Path(ingest_markdown_path).name,
        }

    def retrieval_check(self, provider_refs: dict[str, Any], request: Any) -> dict[str, Any]:
        return {
            "pass": 1,
            "fail": 0,
            "results": [
                {
                    "query": request.queries[0],
                    "classification": "pass",
                    "expected_rank": 1,
                    "top_document": request.expected_document_name,
                }
            ],
        }


class FailingAdapters(FakeAdapters):
    def ocr_and_archive(
        self,
        source: str,
        model: str,
        optional_payload: dict[str, bool],
        on_submitted: Callable[[str], None],
    ) -> dict[str, Any]:
        on_submitted("job-test-failed")
        raise RuntimeError("provider request failed")


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        state_file=tmp_path / "state.json",
        allowed_source_roots=(tmp_path,),
        paddleocr_token="test-token",
        paddleocr_job_url="https://example.test/ocr/jobs",
        paddleocr_model="PaddleOCR-VL-1.6",
        maxkb_base_url="http://localhost:8080/admin/api",
        maxkb_username="admin",
        maxkb_password="test-password",
        maxkb_workspace_id="default",
        maxkb_knowledge_name="test-knowledge",
        api_key="test-worker-key",
    )


def auth_headers(**values: str) -> dict[str, str]:
    return {"Authorization": "Bearer test-worker-key", **values}


def request_payload(source: Path) -> dict[str, Any]:
    return {
        "metadata": {
            "organizationId": "org-test",
            "projectId": "project-test",
            "contractPackageId": "contract-test",
            "sectionId": "section-lj",
            "supervisionSectionId": "supervision-jd-a1",
            "teamId": "team-test",
            "subcontractTeamId": "team-test",
            "reviewTaskId": "opening-condition-test",
            "basisVersionId": "basis-2026-07",
            "documentType": "business_license",
            "sourceObjectId": "evidence-test",
            "sourceObjectType": "pdf",
            "sourceFileName": source.name,
            "masterDataIds": ["master-team-test"],
            "evidenceIds": ["evidence-test"],
            "effectiveStatus": "current",
        },
        "source": {"mode": "local_path", "path": str(source)},
        "runAsync": False,
    }


def test_full_ingestion_flow(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(tmp_path))
    client = TestClient(app)

    created = client.post(
        "/api/preflight/ocr-ingestions",
        json=request_payload(source),
        headers=auth_headers(**{"Idempotency-Key": "full-ingestion-flow"}),
    )
    assert created.status_code == 202
    record = created.json()
    assert record["status"] == "ready_for_ingest"
    assert "resolvedSource" not in record
    assert "requestFingerprint" not in record

    ingestion_id = record["ingestionId"]
    ingested = client.post(
        f"/api/preflight/ocr-ingestions/{ingestion_id}/ingest-to-knowledge",
        json={"provider": "maxkb", "workspaceId": "default"},
        headers=auth_headers(),
    )
    assert ingested.json()["status"] == "ingested"

    checked = client.post(
        f"/api/preflight/ocr-ingestions/{ingestion_id}/retrieval-check",
        json={
            "queries": ["统一社会信用代码 91310115515002x94"],
            "expectedDocumentName": "business-license-ingest.md",
        },
        headers=auth_headers(),
    )
    assert checked.json()["status"] == "retrieval_checked"
    assert checked.json()["retrievalCheck"]["pass"] == 1


def test_rejects_source_outside_allowed_roots(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"test")
    settings = settings_for(allowed)
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(allowed))
    client = TestClient(app)

    response = client.post(
        "/api/preflight/ocr-ingestions",
        json=request_payload(outside),
        headers=auth_headers(**{"Idempotency-Key": "outside-source-test"}),
    )
    assert response.status_code == 400
    assert "outside configured allowed roots" in response.json()["detail"]


def test_business_api_rejects_missing_bearer(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(tmp_path))

    response = TestClient(app).post(
        "/api/preflight/ocr-ingestions",
        json=request_payload(source),
        headers={"Idempotency-Key": "missing-bearer-test"},
    )

    assert response.status_code == 401


def test_create_ingestion_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    adapters = FakeAdapters(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), adapters)
    client = TestClient(app)
    headers = auth_headers(**{"Idempotency-Key": "evidence-test-v1"})

    first = client.post("/api/preflight/ocr-ingestions", json=request_payload(source), headers=headers)
    second = client.post("/api/preflight/ocr-ingestions", json=request_payload(source), headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["ingestionId"] == first.json()["ingestionId"]
    assert adapters.ocr_calls == 1


def test_idempotent_retry_does_not_require_source_file_to_still_exist(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    adapters = FakeAdapters(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), adapters)
    client = TestClient(app)
    headers = auth_headers(**{"Idempotency-Key": "temporary-source-v1"})

    first = client.post("/api/preflight/ocr-ingestions", json=request_payload(source), headers=headers)
    source.unlink()
    retried = client.post("/api/preflight/ocr-ingestions", json=request_payload(source), headers=headers)

    assert first.status_code == 202
    assert retried.status_code == 202
    assert retried.json()["ingestionId"] == first.json()["ingestionId"]
    assert adapters.ocr_calls == 1


def test_idempotency_key_reuse_with_different_request_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    adapters = FakeAdapters(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), adapters)
    client = TestClient(app)
    headers = auth_headers(**{"Idempotency-Key": "evidence-conflict-v1"})
    changed_payload = request_payload(source)
    changed_payload["metadata"]["sourceObjectId"] = "evidence-other"

    first = client.post("/api/preflight/ocr-ingestions", json=request_payload(source), headers=headers)
    conflict = client.post("/api/preflight/ocr-ingestions", json=changed_payload, headers=headers)

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "Idempotency key was already used for a different request."
    assert adapters.ocr_calls == 1


def test_platform_correlation_id_is_preserved(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(tmp_path))
    client = TestClient(app)
    headers = auth_headers(
        **{
            "Idempotency-Key": "correlation-test-v1",
            "X-Correlation-ID": "platform-review-task-001",
        }
    )

    created = client.post("/api/preflight/ocr-ingestions", json=request_payload(source), headers=headers)
    persisted = client.get(
        f"/api/preflight/ocr-ingestions/{created.json()['ingestionId']}",
        headers=auth_headers(),
    )

    assert created.json()["correlationId"] == "platform-review-task-001"
    assert persisted.json()["correlationId"] == "platform-review-task-001"


def test_organization_metadata_is_passed_to_postprocess(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    adapters = FakeAdapters(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), adapters)

    response = TestClient(app).post(
        "/api/preflight/ocr-ingestions",
        json=request_payload(source),
        headers=auth_headers(**{"Idempotency-Key": "metadata-contract-test"}),
    )

    assert response.status_code == 202
    assert adapters.postprocess_metadata["section_id"] == "section-lj"
    assert adapters.postprocess_metadata["supervision_section_id"] == "supervision-jd-a1"
    assert adapters.postprocess_metadata["subcontract_team_id"] == "team-test"
    assert adapters.postprocess_metadata["basis_version_id"] == "basis-2026-07"
    assert adapters.postprocess_metadata["master_data_ids"] == ["master-team-test"]
    assert adapters.postprocess_metadata["evidence_ids"] == ["evidence-test"]


def test_health_reports_worker_auth_and_capabilities(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(tmp_path))

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["authentication"] == {"configured": True, "scheme": "bearer"}
    assert response.json()["capabilities"]["idempotentSubmission"] is True
    assert response.json()["capabilities"]["correlationPropagation"] is True
    assert response.json()["providers"]["paddleocr_vl"]["status"] == "ready"
    assert response.json()["providers"]["maxkb"]["status"] == "ready"


def test_business_api_is_unavailable_when_worker_auth_is_not_configured(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    object.__setattr__(settings, "api_key", "")
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(tmp_path))

    response = TestClient(app).post(
        "/api/preflight/ocr-ingestions",
        json=request_payload(source),
        headers={"Idempotency-Key": "missing-worker-config"},
    )

    assert response.status_code == 503


def test_health_reports_maxkb_unconfigured_without_password(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("PREFLIGHT_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PREFLIGHT_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("PREFLIGHT_ALLOWED_SOURCE_ROOTS", str(tmp_path))
    monkeypatch.delenv("PADDLEOCR_TOKEN", raising=False)
    monkeypatch.delenv("MAXKB_PASSWORD", raising=False)

    settings = Settings.from_env()
    app = create_app(settings, JsonStateStore(settings.state_file), FakeAdapters(tmp_path))
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["providers"]["maxkb"]["configured"] is False


def test_pipeline_failure_is_persisted_with_safe_shape(tmp_path: Path) -> None:
    source = tmp_path / "license.pdf"
    source.write_bytes(b"test")
    settings = settings_for(tmp_path)
    app = create_app(settings, JsonStateStore(settings.state_file), FailingAdapters(tmp_path))
    client = TestClient(app)

    created = client.post(
        "/api/preflight/ocr-ingestions",
        json=request_payload(source),
        headers=auth_headers(**{"Idempotency-Key": "pipeline-failure-test"}),
    )

    assert created.status_code == 202
    record = created.json()
    assert record["status"] == "failed"
    assert record["error"] == {
        "type": "ocr_pipeline_error",
        "summary": "provider request failed",
        "safeDiagnostics": {"exceptionType": "RuntimeError"},
    }
    persisted = client.get(
        f"/api/preflight/ocr-ingestions/{record['ingestionId']}",
        headers=auth_headers(),
    ).json()
    assert persisted["error"] == record["error"]
