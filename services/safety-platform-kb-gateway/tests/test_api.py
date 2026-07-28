# coding=utf-8
"""Public API tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("GATEWAY_API_KEY", "test-api-key")
os.environ.setdefault("MAXKB_BASE_URL", "http://localhost:8080/admin/api")
os.environ.setdefault("MAXKB_USERNAME", "admin")
os.environ.setdefault("MAXKB_PASSWORD", "password")
os.environ.setdefault("MAXKB_WORKSPACE_ID", "default")

from safety_platform_kb_gateway.main import app, get_adapter  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-api-key"}


def override_adapter(mock_adapter: MagicMock) -> None:
    app.dependency_overrides[get_adapter] = lambda: mock_adapter


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_health_returns_ready():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_upload_requires_auth():
    response = client.post("/api/teams/t1/documents", files={"file": ("demo.docx", b"PK")})
    assert response.status_code == 401


def test_upload_rejects_unsupported_type():
    override_adapter(MagicMock())
    response = client.post("/api/teams/t1/documents", headers=AUTH, files={"file": ("demo.exe", b"x")})
    clear_overrides()
    assert response.status_code == 400


def test_upload_auto_creates_knowledge_base():
    adapter = MagicMock()
    adapter.ensure_team_kb.return_value = ({"id": "kb-1", "name": "team:t1:T1"}, True)
    adapter.upload_document.return_value = {"provider_document_id": "doc-1", "file_name": "demo.docx"}
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/documents",
        headers=AUTH,
        files={"file": ("demo.docx", b"PK")},
        data={"teamName": "T1", "projectId": "p1", "documentType": "business_license"},
    )
    clear_overrides()
    assert response.status_code == 201
    body = response.json()
    assert body["autoCreatedKb"] is True
    assert body["knowledgeBaseId"] == "kb-1"


def test_upload_uses_explicit_knowledge_base_id():
    adapter = MagicMock()
    adapter.find_knowledge_base.return_value = {"id": "kb-explicit", "name": "explicit"}
    adapter.upload_document.return_value = {"provider_document_id": "doc-2", "file_name": "demo.docx"}
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/documents",
        headers=AUTH,
        files={"file": ("demo.docx", b"PK")},
        data={"knowledgeBaseId": "kb-explicit", "projectId": "p1", "documentType": "business_license"},
    )
    clear_overrides()
    assert response.status_code == 201
    body = response.json()
    assert body["knowledgeBaseId"] == "kb-explicit"
    assert body["autoCreatedKb"] is False


def test_get_team_knowledge_base_not_found():
    adapter = MagicMock()
    adapter.find_team_kb.return_value = None
    override_adapter(adapter)
    response = client.get("/api/teams/t1/knowledge-base", headers=AUTH)
    clear_overrides()
    assert response.status_code == 200
    assert response.json()["exists"] is False


def test_get_team_knowledge_base_by_explicit_id():
    adapter = MagicMock()
    adapter.find_knowledge_base.return_value = {"id": "kb-explicit", "name": "explicit"}
    override_adapter(adapter)
    response = client.get("/api/teams/t1/knowledge-base?knowledgeBaseId=kb-explicit", headers=AUTH)
    clear_overrides()
    assert response.status_code == 200
    body = response.json()
    assert body["knowledgeBaseId"] == "kb-explicit"


def test_search_returns_structured_hits():
    adapter = MagicMock()
    adapter.find_team_kb.return_value = {"id": "kb-1", "name": "team:t1:T1"}
    adapter.search.return_value = [
        {
            "title": "license.md",
            "snippet": "snippet",
            "score": 0.9,
            "source_type": "",
            "document_id": "doc-1",
            "paragraph_id": "p-1",
        }
    ]
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/search",
        headers=AUTH,
        json={"query": "安全生产许可证", "searchMode": "keywords", "topK": 5},
    )
    clear_overrides()
    assert response.status_code == 200
    body = response.json()
    assert body["teamId"] == "t1"
    assert len(body["hits"]) == 1


def test_search_uses_explicit_knowledge_base_id():
    adapter = MagicMock()
    adapter.find_knowledge_base.return_value = {"id": "kb-explicit", "name": "explicit"}
    adapter.search.return_value = []
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/search",
        headers=AUTH,
        json={"query": "安全生产许可证", "knowledgeBaseId": "kb-explicit"},
    )
    clear_overrides()
    assert response.status_code == 200
    assert response.json()["knowledgeBaseId"] == "kb-explicit"


def test_field_search_builds_query():
    adapter = MagicMock()
    adapter.find_team_kb.return_value = {"id": "kb-1", "name": "team:t1:T1"}
    adapter.search.return_value = []
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/search/field",
        headers=AUTH,
        json={"fieldName": "统一社会信用代码", "fieldValue": "913101"},
    )
    clear_overrides()
    assert response.status_code == 200
    assert "统一社会信用代码: 913101" in response.json()["query"]


def test_delete_team_knowledge_base_404():
    adapter = MagicMock()
    adapter.delete_team_kb.return_value = False
    override_adapter(adapter)
    response = client.delete("/api/teams/t1/knowledge-base", headers=AUTH)
    clear_overrides()
    assert response.status_code == 404


def test_delete_team_knowledge_base_by_explicit_id():
    adapter = MagicMock()
    adapter.delete_knowledge_base.return_value = True
    override_adapter(adapter)
    response = client.delete("/api/teams/t1/knowledge-base?knowledgeBaseId=kb-explicit", headers=AUTH)
    clear_overrides()
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_delete_team_knowledge_base_requires_explicit_id_when_protected():
    os.environ["REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE"] = "true"
    override_adapter(MagicMock())
    response = client.delete("/api/teams/t1/knowledge-base", headers=AUTH)
    clear_overrides()
    del os.environ["REQUIRE_KNOWLEDGE_BASE_ID_FOR_DELETE"]
    assert response.status_code == 400
    assert "knowledgeBaseId" in response.json()["detail"]


def test_sync_basis_returns_batch_result():
    adapter = MagicMock()
    adapter.ensure_team_kb.return_value = ({"id": "kb-1", "name": "team:t1:T1"}, False)
    adapter.upload_document.return_value = {"provider_document_id": "doc-1", "file_name": "basis.docx"}
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/knowledge-base/sync-basis",
        headers=AUTH,
        files=[("files", ("basis1.docx", b"a")), ("files", ("basis2.docx", b"b"))],
        data={"projectId": "p1", "sourceTable": "biz_system_document"},
    )
    clear_overrides()
    assert response.status_code == 201
    assert response.json()["uploadedCount"] == 2


def test_upload_returns_source_metadata_and_content_hash():
    adapter = MagicMock()
    adapter.ensure_team_kb.return_value = ({"id": "kb-1", "name": "team:t1:T1"}, False)
    adapter.upload_document.return_value = {"provider_document_id": "doc-1", "file_name": "license.pdf"}
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/documents",
        headers=AUTH,
        files={"file": ("license.pdf", b"license-content")},
        data={
            "projectId": "p1",
            "documentType": "business_license",
            "sourceTable": "biz_work_team",
            "sourceObjectId": "team-1",
        },
    )
    clear_overrides()
    assert response.status_code == 201
    metadata = response.json()["metadata"]
    assert metadata["scope"] == "team_private"
    assert metadata["sourceObjectId"] == "team-1"
    assert len(metadata["contentHash"]) == 64


def test_project_shared_upload_requires_source_table():
    adapter = MagicMock()
    override_adapter(adapter)
    response = client.post(
        "/api/teams/t1/documents",
        headers=AUTH,
        files={"file": ("basis.pdf", b"basis")},
        data={"projectId": "p1", "documentType": "project_basis", "scope": "project_shared"},
    )
    clear_overrides()
    assert response.status_code == 400
