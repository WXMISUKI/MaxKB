# coding=utf-8
"""FastAPI entrypoint for the safety platform knowledge gateway."""

from __future__ import annotations

import hashlib
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile

from .adapters import GatewayAdapter, MaxKBError, is_supported_file
from .config import Settings
from .schemas import (
    DocumentDeleteResponse,
    DocumentUploadResponse,
    FieldSearchRequest,
    HealthResponse,
    KnowledgeBaseDeleteResponse,
    KnowledgeBaseStatus,
    DocumentMetadata,
    SearchDiagnostics,
    SearchHit,
    SearchResponse,
    SyncBasisResponse,
    TeamSearchRequest,
)
from .security import get_settings, require_api_key


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="Safety Platform Knowledge Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


def get_adapter(settings: Settings = Depends(get_settings)) -> GatewayAdapter:
    return GatewayAdapter(settings)


def handle_maxkb_error(exc: MaxKBError) -> None:
    raise HTTPException(status_code=500, detail=str(exc))


def save_upload(upload: UploadFile) -> tuple[Path, str]:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
    if not is_supported_file(upload.filename):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {Path(upload.filename).suffix}")
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.filename).suffix)
    content = upload.file.read()
    tmp_file.write(content)
    tmp_file.flush()
    tmp_file.close()
    return Path(tmp_file.name), hashlib.sha256(content).hexdigest()


def build_document_metadata(
    *,
    team_id: str,
    scope: str,
    project_id: str,
    document_type: str,
    project_name: str = "",
    source_type: str = "",
    source_table: str = "",
    source_object_id: str = "",
    basis_version_id: str = "",
    content_hash: str = "",
    effective_status: str = "",
    effective_date: str = "",
) -> DocumentMetadata:
    if scope not in {"team_private", "project_shared"}:
        raise HTTPException(status_code=400, detail="scope must be team_private or project_shared.")
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required.")
    if not document_type:
        raise HTTPException(status_code=400, detail="documentType is required.")
    if scope == "project_shared" and not source_table:
        raise HTTPException(status_code=400, detail="sourceTable is required for project_shared documents.")
    return DocumentMetadata(
        scope=scope,
        project_id=project_id,
        document_type=document_type,
        project_name=project_name,
        source_type=source_type,
        source_table=source_table,
        source_object_id=source_object_id,
        basis_version_id=basis_version_id,
        content_hash=content_hash,
        effective_status=effective_status,
        effective_date=effective_date,
    )


def resolve_knowledge_base(
    adapter: GatewayAdapter,
    workspace_id: str,
    team_id: str,
    knowledge_base_id: str = "",
    team_name: str = "",
    project_name: str = "",
    create_if_missing: bool = True,
):
    if knowledge_base_id:
        knowledge = adapter.find_knowledge_base(workspace_id, knowledge_base_id)
        if not knowledge:
            raise MaxKBError(f"Knowledge base {knowledge_base_id} was not found.")
        return knowledge, False
    return adapter.ensure_team_kb(
        workspace_id,
        team_id,
        team_name=team_name,
        project_name=project_name,
        create_if_missing=create_if_missing,
    )


@app.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)):
    maxkb_ready = settings.maxkb_ready
    auth_ready = bool(settings.api_key)
    ready = maxkb_ready and auth_ready
    return HealthResponse(
        service="safety-platform-kb-gateway",
        ready=ready,
        status="ready" if ready else "degraded",
        authentication={"configured": auth_ready, "scheme": "bearer"},
        capabilities={
            "document_upload": True,
            "knowledge_base_management": True,
            "search": True,
            "field_search": True,
            "basis_sync": True,
        },
        providers={
            "maxkb": {
                "provider": "maxkb",
                "configured": maxkb_ready,
                "ready": maxkb_ready,
                "status": "ready" if maxkb_ready else "disabled",
                "workspaceId": settings.maxkb_workspace_id,
            }
        },
    )


@app.post("/api/teams/{team_id}/documents", response_model=DocumentUploadResponse, status_code=201)
def upload_team_document(
    team_id: str,
    file: UploadFile = File(...),
    team_name: str = Form(""),
    project_name: str = Form(""),
    document_type: str = Form("", alias="documentType"),
    scope: str = Form("team_private"),
    project_id: str = Form("", alias="projectId"),
    source_type: str = Form(""),
    source_table: str = Form("", alias="sourceTable"),
    source_object_id: str = Form("", alias="sourceObjectId"),
    basis_version_id: str = Form("", alias="basisVersionId"),
    content_hash: str = Form("", alias="contentHash"),
    effective_status: str = Form(""),
    effective_date: str = Form(""),
    knowledge_base_id: str = Form("", alias="knowledgeBaseId"),
    create_if_missing: bool = Form(True),
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    temp_path, computed_hash = save_upload(file)
    try:
        metadata = build_document_metadata(
            team_id=team_id,
            scope=scope,
            project_id=project_id,
            document_type=document_type,
            project_name=project_name,
            source_type=source_type,
            source_table=source_table,
            source_object_id=source_object_id,
            basis_version_id=basis_version_id,
            content_hash=content_hash or computed_hash,
            effective_status=effective_status,
            effective_date=effective_date,
        )
    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    try:
        knowledge, auto_created = resolve_knowledge_base(
            adapter,
            settings.maxkb_workspace_id,
            team_id,
            knowledge_base_id=knowledge_base_id,
            team_name=team_name,
            project_name=project_name,
            create_if_missing=create_if_missing,
        )
    except MaxKBError as exc:
        temp_path.unlink(missing_ok=True)
        handle_maxkb_error(exc)
    try:
        result = adapter.upload_document(settings.maxkb_workspace_id, knowledge["id"], temp_path)
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    finally:
        temp_path.unlink(missing_ok=True)
    return DocumentUploadResponse(
        team_id=team_id,
        knowledge_base_id=knowledge["id"],
        provider_document_id=result["provider_document_id"],
        file_name=result["file_name"],
        metadata=metadata,
        auto_created_kb=auto_created,
    )


@app.get("/api/teams/{team_id}/knowledge-base", response_model=KnowledgeBaseStatus)
def get_team_knowledge_base(
    team_id: str,
    knowledge_base_id: str = Query("", alias="knowledgeBaseId"),
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    try:
        knowledge = (
            adapter.find_knowledge_base(settings.maxkb_workspace_id, knowledge_base_id)
            if knowledge_base_id
            else adapter.find_team_kb(settings.maxkb_workspace_id, team_id)
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    if not knowledge:
        return KnowledgeBaseStatus(team_id=team_id, exists=False)
    return KnowledgeBaseStatus(
        team_id=team_id,
        knowledge_base_id=knowledge["id"],
        knowledge_base_name=knowledge.get("name", ""),
        exists=True,
    )


@app.delete("/api/teams/{team_id}/knowledge-base", response_model=KnowledgeBaseDeleteResponse)
def delete_team_knowledge_base(
    team_id: str,
    knowledge_base_id: str = Query("", alias="knowledgeBaseId"),
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    try:
        deleted = (
            adapter.delete_knowledge_base(settings.maxkb_workspace_id, knowledge_base_id)
            if knowledge_base_id
            else adapter.delete_team_kb(settings.maxkb_workspace_id, team_id)
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Knowledge base for team {team_id} not found.")
    return KnowledgeBaseDeleteResponse(team_id=team_id, deleted=True)


@app.delete("/api/teams/{team_id}/documents/{document_id}", response_model=DocumentDeleteResponse)
def delete_team_document(
    team_id: str,
    document_id: str,
    knowledge_base_id: str = Query("", alias="knowledgeBaseId"),
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    try:
        knowledge = (
            adapter.find_knowledge_base(settings.maxkb_workspace_id, knowledge_base_id)
            if knowledge_base_id
            else adapter.find_team_kb(settings.maxkb_workspace_id, team_id)
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    if not knowledge:
        raise HTTPException(status_code=404, detail=f"Knowledge base for team {team_id} not found.")
    try:
        adapter.delete_document(settings.maxkb_workspace_id, knowledge["id"], document_id)
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    return DocumentDeleteResponse(team_id=team_id, document_id=document_id, deleted=True)


@app.post("/api/teams/{team_id}/search", response_model=SearchResponse)
def search_team(
    team_id: str,
    body: TeamSearchRequest,
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    try:
        knowledge = (
            adapter.find_knowledge_base(settings.maxkb_workspace_id, body.knowledge_base_id)
            if body.knowledge_base_id
            else adapter.find_team_kb(settings.maxkb_workspace_id, team_id)
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    if not knowledge:
        raise HTTPException(status_code=404, detail=f"Knowledge base for team {team_id} not found.")
    try:
        raw_hits = adapter.search(
            settings.maxkb_workspace_id,
            knowledge["id"],
            body.query,
            body.search_mode,
            body.top_k,
            body.similarity,
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    hits = [SearchHit(**item) for item in raw_hits]
    return SearchResponse(
        team_id=team_id,
        knowledge_base_id=knowledge["id"],
        query=body.query,
        hits=hits,
        diagnostics=SearchDiagnostics(
            search_mode=body.search_mode,
            total_hits=len(hits),
            workspace_id=settings.maxkb_workspace_id,
        ),
    )


@app.post("/api/teams/{team_id}/search/field", response_model=SearchResponse)
def search_team_field(
    team_id: str,
    body: FieldSearchRequest,
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    field_query = f"{body.field_name}: {body.field_value}"
    try:
        knowledge = (
            adapter.find_knowledge_base(settings.maxkb_workspace_id, body.knowledge_base_id)
            if body.knowledge_base_id
            else adapter.find_team_kb(settings.maxkb_workspace_id, team_id)
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    if not knowledge:
        raise HTTPException(status_code=404, detail=f"Knowledge base for team {team_id} not found.")
    try:
        raw_hits = adapter.search(
            settings.maxkb_workspace_id,
            knowledge["id"],
            field_query,
            body.search_mode,
            body.top_k,
            body.similarity,
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    hits = [SearchHit(**item) for item in raw_hits]
    return SearchResponse(
        team_id=team_id,
        knowledge_base_id=knowledge["id"],
        query=field_query,
        hits=hits,
        diagnostics=SearchDiagnostics(
            search_mode=body.search_mode,
            total_hits=len(hits),
            workspace_id=settings.maxkb_workspace_id,
        ),
    )


@app.post("/api/teams/{team_id}/knowledge-base/sync-basis", response_model=SyncBasisResponse, status_code=201)
def sync_basis(
    team_id: str,
    files: list[UploadFile] = File(...),
    project_id: str = Form("", alias="projectId"),
    project_name: str = Form(""),
    source_table: str = Form("", alias="sourceTable"),
    basis_version_id: str = Form("", alias="basisVersionId"),
    knowledge_base_id: str = Form("", alias="knowledgeBaseId"),
    create_if_missing: bool = Form(True),
    _token: str = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
    adapter: GatewayAdapter = Depends(get_adapter),
):
    try:
        knowledge, _ = resolve_knowledge_base(
            adapter,
            settings.maxkb_workspace_id,
            team_id,
            knowledge_base_id=knowledge_base_id,
            create_if_missing=create_if_missing,
        )
    except MaxKBError as exc:
        handle_maxkb_error(exc)
    results: list[DocumentUploadResponse] = []
    for upload in files:
        if not upload.filename:
            continue
        temp_path, computed_hash = save_upload(upload)
        try:
            metadata = build_document_metadata(
                team_id=team_id,
                scope="project_shared",
                project_id=project_id,
                document_type="project_basis",
                project_name=project_name,
                source_table=source_table,
                basis_version_id=basis_version_id,
                content_hash=computed_hash,
            )
        except HTTPException:
            temp_path.unlink(missing_ok=True)
            raise
        try:
            result = adapter.upload_document(settings.maxkb_workspace_id, knowledge["id"], temp_path)
        except MaxKBError as exc:
            handle_maxkb_error(exc)
        finally:
            temp_path.unlink(missing_ok=True)
        results.append(
            DocumentUploadResponse(
                team_id=team_id,
                knowledge_base_id=knowledge["id"],
                provider_document_id=result["provider_document_id"],
                file_name=result["file_name"],
                metadata=metadata,
                auto_created_kb=False,
            )
        )
    return SyncBasisResponse(
        team_id=team_id,
        knowledge_base_id=knowledge["id"],
        uploaded_count=len(results),
        results=results,
    )
