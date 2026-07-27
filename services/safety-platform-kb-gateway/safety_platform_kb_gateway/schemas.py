# coding=utf-8
"""Gateway schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(item.title() for item in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HealthResponse(ApiModel):
    service: str
    ready: bool
    status: Literal["ready", "degraded"]
    authentication: dict[str, Any]
    capabilities: dict[str, bool]
    providers: dict[str, dict[str, Any]]


class TeamSearchRequest(ApiModel):
    query: str = Field(min_length=1)
    knowledge_base_id: str = ""
    search_mode: Literal["keywords", "blend", "embedding"] = "blend"
    top_k: int = Field(default=8, ge=1, le=50)
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class FieldSearchRequest(ApiModel):
    field_name: str = Field(min_length=1)
    field_value: str = Field(min_length=1)
    knowledge_base_id: str = ""
    search_mode: Literal["keywords", "blend", "embedding"] = "keywords"
    top_k: int = Field(default=5, ge=1, le=50)
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchHit(ApiModel):
    title: str
    snippet: str
    score: float | None = None
    source_type: str = ""
    document_id: str = ""
    paragraph_id: str = ""


class SearchDiagnostics(ApiModel):
    search_mode: str
    total_hits: int
    provider: str = "maxkb"
    workspace_id: str = ""


class SearchResponse(ApiModel):
    team_id: str
    knowledge_base_id: str
    query: str
    hits: list[SearchHit]
    diagnostics: SearchDiagnostics


class DocumentMetadata(ApiModel):
    scope: Literal["team_private", "project_shared"]
    project_id: str
    document_type: str
    project_name: str = ""
    source_type: str = ""
    source_table: str = ""
    source_object_id: str = ""
    basis_version_id: str = ""
    content_hash: str = ""
    effective_status: str = ""
    effective_date: str = ""


class DocumentUploadResponse(ApiModel):
    team_id: str
    knowledge_base_id: str
    provider_document_id: str
    file_name: str
    metadata: DocumentMetadata
    auto_created_kb: bool = False


class KnowledgeBaseStatus(ApiModel):
    team_id: str
    knowledge_base_id: str = ""
    knowledge_base_name: str = ""
    exists: bool


class KnowledgeBaseDeleteResponse(ApiModel):
    team_id: str
    deleted: bool


class DocumentDeleteResponse(ApiModel):
    team_id: str
    document_id: str
    deleted: bool


class SyncBasisResponse(ApiModel):
    team_id: str
    knowledge_base_id: str
    uploaded_count: int
    results: list[DocumentUploadResponse]
