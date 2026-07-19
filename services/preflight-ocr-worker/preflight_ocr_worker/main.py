from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, status

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
from .store import JsonStateStore


def public_record(record: dict) -> dict:
    def convert(value):
        if isinstance(value, dict):
            return {
                "".join([parts[0], *[item.title() for item in parts[1:]]]): convert(item)
                for key, item in value.items()
                if key != "resolved_source"
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

    @app.get("/health", response_model=HealthResponse, response_model_by_alias=True)
    def health() -> HealthResponse:
        paddle_configured = bool(settings.paddleocr_token)
        maxkb_configured = bool(settings.maxkb_base_url and settings.maxkb_username and settings.maxkb_password)
        ready = paddle_configured and maxkb_configured
        return HealthResponse(
            service="preflight-ocr-worker",
            ready=ready,
            status="ready" if ready else "degraded",
            providers={
                "paddleocr_vl": {
                    "configured": paddle_configured,
                    "ready": paddle_configured,
                    "model": settings.paddleocr_model,
                },
                "maxkb": {
                    "configured": maxkb_configured,
                    "ready": maxkb_configured,
                    "workspaceId": settings.maxkb_workspace_id,
                },
            },
        )

    @app.post("/api/preflight/ocr-ingestions", status_code=status.HTTP_202_ACCEPTED)
    def create_ingestion(request: CreateIngestionRequest, background_tasks: BackgroundTasks) -> dict:
        try:
            record = service.create(request)
        except (ValueError, PermissionError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if request.run_async:
            background_tasks.add_task(service.run_ocr_pipeline, record["ingestion_id"])
            return public_record(service._transition(record["ingestion_id"], "ocr_pending"))
        return public_record(service.run_ocr_pipeline(record["ingestion_id"]))

    @app.get("/api/preflight/ocr-ingestions/{ingestion_id}")
    def get_ingestion(ingestion_id: str) -> dict:
        record = service.get(ingestion_id)
        if not record:
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(record)

    @app.post("/api/preflight/ocr-ingestions/{ingestion_id}/postprocess")
    def postprocess_ingestion(ingestion_id: str, request: PostprocessRequest) -> dict:
        if not service.get(ingestion_id):
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(service.run_postprocess(ingestion_id, request))

    @app.post("/api/preflight/ocr-ingestions/{ingestion_id}/ingest-to-knowledge")
    def ingest_to_knowledge(ingestion_id: str, request: IngestKnowledgeRequest) -> dict:
        if not service.get(ingestion_id):
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(service.ingest_to_knowledge(ingestion_id, request))

    @app.post("/api/preflight/ocr-ingestions/{ingestion_id}/retrieval-check")
    def retrieval_check(ingestion_id: str, request: RetrievalCheckRequest) -> dict:
        if not service.get(ingestion_id):
            raise HTTPException(status_code=404, detail="Ingestion record not found.")
        return public_record(service.retrieval_check(ingestion_id, request))

    return app


app = create_app()
