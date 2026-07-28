FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PREFLIGHT_PROJECT_ROOT=/app \
    PREFLIGHT_STATE_FILE=/var/preflight-ocr-worker/state.json \
    PREFLIGHT_ALLOWED_SOURCE_ROOTS=/data/sources

WORKDIR /app

COPY services/preflight-ocr-worker/pyproject.toml /app/services/preflight-ocr-worker/pyproject.toml
COPY services/preflight-ocr-worker/preflight_ocr_worker /app/services/preflight-ocr-worker/preflight_ocr_worker
COPY docs/construction-supervision-local-validation/scripts /app/docs/construction-supervision-local-validation/scripts

RUN mkdir -p \
      /var/preflight-ocr-worker \
      /data/sources \
      /app/docs/simulated-pilot-dataset/NJDL-JD-A1/00_manifest/00_ocr_outputs \
    && pip install --no-cache-dir \
      "fastapi==0.115.0" \
      "uvicorn==0.30.6" \
      "pydantic==2.10.6" \
      "requests>=2.31,<3"

EXPOSE 8091

WORKDIR /app/services/preflight-ocr-worker

CMD ["uvicorn", "preflight_ocr_worker.main:app", "--host", "0.0.0.0", "--port", "8091"]
