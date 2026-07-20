from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(item.title() for item in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class EvidenceMetadata(ApiModel):
    organization_id: str
    project_id: str
    project_name: str = ""
    contract_package_id: str
    section_id: str = ""
    supervision_section_id: str = ""
    team_id: str
    team_name: str = ""
    subcontract_team_id: str = ""
    review_task_id: str
    basis_version_id: str = ""
    document_type: str
    source_object_id: str
    source_object_type: Literal["pdf", "image", "office", "url"]
    source_file_name: str
    source_file_path: str = ""
    content_hash: str = ""
    master_data_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    effective_status: str = ""
    effective_date: str = ""
    indexed_at: str = ""


class SourceSpec(ApiModel):
    mode: Literal["local_path", "url"]
    path: str = ""
    url: str = ""

    @model_validator(mode="after")
    def validate_source(self) -> "SourceSpec":
        if self.mode == "local_path" and not self.path:
            raise ValueError("path is required for local_path mode")
        if self.mode == "url" and not self.url:
            raise ValueError("url is required for url mode")
        return self


class OcrOptions(ApiModel):
    provider: Literal["paddleocr_vl"] = "paddleocr_vl"
    model: str = "PaddleOCR-VL-1.6"
    optional_payload: dict[str, bool] = Field(
        default_factory=lambda: {
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }
    )


class CreateIngestionRequest(ApiModel):
    metadata: EvidenceMetadata
    source: SourceSpec
    ocr: OcrOptions = Field(default_factory=OcrOptions)
    run_async: bool = True


class PostprocessRequest(ApiModel):
    certificate_type: Literal[
        "auto",
        "business_license",
        "safety_production_license",
        "personnel_certificate",
    ] = "auto"


class IngestKnowledgeRequest(ApiModel):
    provider: Literal["maxkb"] = "maxkb"
    workspace_id: str = "default"
    knowledge_base_id: str = ""
    knowledge_name: str = ""
    confirm_postprocess_warnings: bool = False


class RetrievalCheckRequest(ApiModel):
    search_mode: Literal["keywords", "blend", "embedding"] = "keywords"
    queries: list[str] = Field(min_length=1)
    expected_document_name: str
    top_number: int = Field(default=8, ge=1, le=50)
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class KnowledgeSearchRequest(ApiModel):
    query_text: str = Field(alias="queryText", min_length=1)
    search_mode: Literal["keywords", "blend", "embedding"] = "blend"
    top_number: int = Field(default=8, ge=1, le=50)
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class HealthResponse(ApiModel):
    service: str
    ready: bool
    status: Literal["ready", "degraded"]
    authentication: dict[str, Any]
    capabilities: dict[str, bool]
    providers: dict[str, dict[str, Any]]
