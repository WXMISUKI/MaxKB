from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status

from .adapters import ProviderAdapters
from .config import Settings
from .schemas import (
    CreateIngestionRequest,
    HealthResponse,
    IngestKnowledgeRequest,
    PostprocessRequest,
    RetrievalCheckRequest,
)
from .service import IngestionService
from .store import IdempotencyConflict, JsonStateStore


def public_record(record: dict) -> dict:
    def convert(value):
        if isinstance(value, dict):
            return {
                "".join([parts[0], *[item.title() for item in parts[1:]]]): convert(item)
                for key, item in value.items()
                if key not in {"resolved_source", "request_fingerprint"}
                for parts in [key.split("_")]
            }
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    return convert(record)


def create_app(
    settings: Settings | None = None,
    store: JsonStateStore | None = None,
    adapters: ProviderAdapters | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store or JsonStateStore(settings.state_file)
    adapters = adapters or ProviderAdapters(settings)
    service = IngestionService(settings, store, adapters)

    app = FastAPI(
        title="Preflight OCR Worker",
        version="0.1.0",
        description="OCR, certificate post-processing, MaxKB ingestion, and retrieval validation worker.",
    )
    app.state.settings = settings
    app.state.service = service

    def require_api_key(authorization: str | None = Header(default=None)) -> None:
        if not settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Worker API authentication is not configured.",
            )
        scheme, _, credential = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(credential, settings.api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid worker API credential.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/health", response_model=HealthResponse, response_model_by_alias=True)
    def health() -> HealthResponse:
        auth_configured = bool(settings.api_key)
        paddle_configured = bool(settings.paddleocr_token)
        maxkb_configured = bool(settings.maxkb_base_url and settings.maxkb_username and settings.maxkb_password)
        ready = auth_configured and paddle_configured and maxkb_configured
        return HealthResponse(
            service="preflight-ocr-worker",
            ready=ready,
            status="ready" if ready else "degraded",
            authentication={
                "configured": auth_configured,
                "scheme": "bearer",
            },
            capabilities={
                "ocr": True,
                "certificatePostprocess": True,
                "knowledgeIngestion": True,
                "retrievalCheck": True,
                "idempotentSubmission": True,
                "correlationPropagation": True,
            },
            providers={
                "paddleocr_vl": {
                    "provider": "paddleocr_vl",
                    "configured": paddle_configured,
                    "ready": paddle_configured,
                    "status": "ready" if paddle_configured else "disabled",
                    "summary": (
                        "PaddleOCR-VL is configured."
                        if paddle_configured
                        else "PaddleOCR-VL credential is not configured."
                    ),
                    "model": settings.paddleocr_model,
                    "capabilities": {"ocr": True},
                },
                "maxkb": {
                    "provider": "maxkb",
                    "configured": maxkb_configured,
                    "ready": maxkb_configured,
                    "status": "ready" if maxkb_configured else "disabled",
                    "summary": (
                        "MaxKB knowledge provider is configured."
                        if maxkb_configured
                        else "MaxKB credential is not configured."
                    ),
                    "workspaceId": settings.maxkb_workspace_id,
                    "capabilities": {
                        "ingestion": True,
                        "retrieval": True,
                        "documentStatus": False,
                    },
                },
            },
        )

    @app.post(
        "/api/preflight/ocr-ingestions",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_api_key)],
    )
    def create_ingestion(
        request: CreateIngestionRequest,
        background_tasks: BackgroundTasks,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
        correlation_id: Annotated[
            str | None,
            Header(alias="X-Correlation-ID", min_length=1, max_length=200),
        ] = None,
    ) -> dict:
        try:
            record, created = service.create(request, idempotency_key, correlation_id)
        except (ValueError, PermissionError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except IdempotencyConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if not created:
            return public_record(record)
        if request.run_async:
            background_tasks.add_task(service.run_ocr_pipeline, record["ingestion_id"])
            return public_record(service._transition(record["ingestion_id"], "ocr_pending"))
        return public_record(service.run_ocr_pipeline(record["ingestion_id"]))

    @app.get("/api/preflight/ocr-ingestions/{ingestion_id}", dependencies=[Depends(require_api_key)])
    def get_ingestion(ingestion_id: str) -> dict:
        record = service.get(ingestion_id)
        if not record:
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(record)

    @app.post(
        "/api/preflight/ocr-ingestions/{ingestion_id}/postprocess",
        dependencies=[Depends(require_api_key)],
    )
    def postprocess_ingestion(ingestion_id: str, request: PostprocessRequest) -> dict:
        if not service.get(ingestion_id):
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(service.run_postprocess(ingestion_id, request))

    @app.post(
        "/api/preflight/ocr-ingestions/{ingestion_id}/ingest-to-knowledge",
        dependencies=[Depends(require_api_key)],
    )
    def ingest_to_knowledge(ingestion_id: str, request: IngestKnowledgeRequest) -> dict:
        if not service.get(ingestion_id):
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(service.ingest_to_knowledge(ingestion_id, request))

    @app.post(
        "/api/preflight/ocr-ingestions/{ingestion_id}/retrieval-check",
        dependencies=[Depends(require_api_key)],
    )
    def retrieval_check(ingestion_id: str, request: RetrievalCheckRequest) -> dict:
        if not service.get(ingestion_id):
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(service.retrieval_check(ingestion_id, request))

    return app


app = create_app()
