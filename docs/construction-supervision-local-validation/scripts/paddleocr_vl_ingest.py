# coding=utf-8
"""
Submit scanned documents to PaddleOCR-VL, archive Markdown output, and optionally
upload the derived Markdown to MaxKB.

Secrets are read from environment variables only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from configure_and_upload_maxkb import (
    DEFAULT_BASE_URL,
    DEFAULT_KNOWLEDGE_NAME,
    DEFAULT_WORKSPACE_ID,
    MaxKBClient,
    MaxKBError,
    PILOT_ROOT,
)

DEFAULT_JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
DEFAULT_MODEL = "PaddleOCR-VL-1.6"
OCR_OUTPUT_ROOT = PILOT_ROOT / "00_manifest" / "00_ocr_outputs"
OCR_RESULT_INDEX = PILOT_ROOT / "00_manifest" / "paddleocr-vl-result.json"


@dataclass
class OcrArtifact:
    source: str
    job_id: str
    state: str
    output_dir: Path
    combined_markdown: Path
    page_count: int
    json_url: str
    markdown_url: str


class PaddleOcrClient:
    def __init__(
        self,
        job_url: str,
        token: str,
        model: str,
        poll_interval: int,
        timeout_seconds: int,
    ) -> None:
        self.job_url = job_url.rstrip("/")
        self.model = model
        self.poll_interval = poll_interval
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"bearer {token}"})

    def submit(self, source: str, optional_payload: dict[str, Any]) -> str:
        if source.startswith(("http://", "https://")):
            headers = {**self.session.headers, "Content-Type": "application/json"}
            payload = {
                "fileUrl": source,
                "model": self.model,
                "optionalPayload": optional_payload,
            }
            response = self.session.post(self.job_url, json=payload, headers=headers, timeout=60)
        else:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            data = {
                "model": self.model,
                "optionalPayload": json.dumps(optional_payload, ensure_ascii=False),
            }
            with path.open("rb") as file:
                response = self.session.post(self.job_url, data=data, files={"file": file}, timeout=120)
        payload = _json_response(response, "submit OCR job")
        return payload["data"]["jobId"]

    def poll(self, job_id: str) -> dict[str, Any]:
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            response = self.session.get(f"{self.job_url}/{job_id}", timeout=60)
            payload = _json_response(response, "poll OCR job")
            data = payload.get("data", {})
            state = data.get("state")
            if state == "done":
                return data
            if state == "failed":
                raise RuntimeError(f"OCR job failed: {data.get('errorMsg', 'unknown error')}")
            if state not in {"pending", "running"}:
                raise RuntimeError(f"Unexpected OCR job state: {state}")
            time.sleep(self.poll_interval)
        raise TimeoutError(f"OCR job timed out after {self.timeout_seconds}s: {job_id}")


def _json_response(response: requests.Response, action: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"{action} returned non-json response: {response.status_code}") from exc
    if response.status_code != 200:
        raise RuntimeError(f"{action} failed: HTTP {response.status_code}, {payload.get('msg') or response.text}")
    code = payload.get("code")
    if code not in (0, 200, None):
        raise RuntimeError(f"{action} failed: code={code}, msg={payload.get('msg')}")
    return payload


def archive_ocr_result(source: str, job_id: str, data: dict[str, Any]) -> OcrArtifact:
    result_url = data.get("resultUrl", {}) or {}
    json_url = result_url.get("jsonUrl") or ""
    markdown_url = result_url.get("markdownUrl") or ""
    if not json_url:
        raise RuntimeError("OCR job completed without jsonUrl.")

    output_dir = OCR_OUTPUT_ROOT / f"{_safe_source_stem(source)}-{job_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_response = requests.get(json_url, timeout=120)
    jsonl_response.raise_for_status()
    jsonl_text = jsonl_response.text
    (output_dir / "raw-result.jsonl").write_text(jsonl_text, encoding="utf-8")

    page_markdowns: list[Path] = []
    page_num = 0
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        result = json.loads(line).get("result", {})
        for item in result.get("layoutParsingResults", []):
            markdown_text = item.get("markdown", {}).get("text", "")
            page_file = output_dir / f"page_{page_num:04d}.md"
            page_file.write_text(markdown_text, encoding="utf-8")
            page_markdowns.append(page_file)
            page_num += 1

    combined = output_dir / f"{_safe_source_stem(source)}-ocr-derived.md"
    combined_text = [f"# OCR Derived Markdown\n\nSource: `{source}`\n\nJob ID: `{job_id}`\n"]
    for index, page_file in enumerate(page_markdowns, start=1):
        combined_text.append(f"\n\n## Page {index}\n\n")
        combined_text.append(page_file.read_text(encoding="utf-8"))
    combined.write_text("".join(combined_text), encoding="utf-8")

    return OcrArtifact(
        source=source,
        job_id=job_id,
        state=data.get("state", ""),
        output_dir=output_dir,
        combined_markdown=combined,
        page_count=len(page_markdowns),
        json_url=json_url,
        markdown_url=markdown_url,
    )


def _safe_source_stem(source: str) -> str:
    parsed = urlparse(source)
    name = Path(parsed.path).name if parsed.scheme else Path(source).name
    if not name:
        name = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    stem = Path(name).stem
    safe_stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._-")
    return (safe_stem or hashlib.sha256(source.encode("utf-8")).hexdigest()[:12])[:80]


def write_index(artifacts: list[OcrArtifact], uploaded: list[dict[str, str]]) -> None:
    OCR_RESULT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    if OCR_RESULT_INDEX.exists():
        payload = json.loads(OCR_RESULT_INDEX.read_text(encoding="utf-8"))
    else:
        payload = {"artifacts": [], "uploads": []}

    artifact_rows = payload.setdefault("artifacts", [])
    upload_rows = payload.setdefault("uploads", [])
    existing_artifacts = {(item.get("source"), item.get("job_id")) for item in artifact_rows}
    for item in artifacts:
        key = (item.source, item.job_id)
        if key in existing_artifacts:
            continue
        artifact_rows.append(
            {
                "source": item.source,
                "job_id": item.job_id,
                "state": item.state,
                "page_count": item.page_count,
                "output_dir": str(item.output_dir),
                "combined_markdown": str(item.combined_markdown),
                "has_json_url": bool(item.json_url),
                "has_markdown_url": bool(item.markdown_url),
            }
        )
    upload_rows.extend(uploaded)
    OCR_RESULT_INDEX.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upload_to_maxkb(args: argparse.Namespace, artifacts: list[OcrArtifact]) -> list[dict[str, str]]:
    client = MaxKBClient(args.maxkb_base_url)
    client.login(args.maxkb_username, args.maxkb_password)
    knowledge = next(
        (item for item in client.list_knowledge(args.workspace_id) if item.get("name") == args.knowledge_name),
        None,
    )
    if not knowledge:
        raise MaxKBError(f"Knowledge base not found: {args.knowledge_name}")

    uploaded = []
    for artifact in artifacts:
        client.upload_text_document(args.workspace_id, knowledge["id"], artifact.combined_markdown)
        uploaded.append(
            {
                "source": artifact.source,
                "derived_markdown": str(artifact.combined_markdown),
                "status": "success",
            }
        )
    return uploaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PaddleOCR-VL and optionally ingest markdown into MaxKB.")
    parser.add_argument("sources", nargs="+", help="Local file paths or HTTP(S) file URLs.")
    parser.add_argument("--job-url", default=os.getenv("PADDLEOCR_JOB_URL", DEFAULT_JOB_URL))
    parser.add_argument("--model", default=os.getenv("PADDLEOCR_MODEL", DEFAULT_MODEL))
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--use-doc-orientation-classify", action="store_true")
    parser.add_argument("--use-doc-unwarping", action="store_true")
    parser.add_argument("--use-chart-recognition", action="store_true")
    parser.add_argument("--upload-to-maxkb", action="store_true")
    parser.add_argument("--maxkb-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--maxkb-username", default="admin")
    parser.add_argument("--maxkb-password", default=os.getenv("MAXKB_PASSWORD", "Admin123@"))
    parser.add_argument("--knowledge-name", default=DEFAULT_KNOWLEDGE_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.getenv("PADDLEOCR_TOKEN")
    if not token:
        raise RuntimeError("PADDLEOCR_TOKEN is required.")

    optional_payload = {
        "useDocOrientationClassify": args.use_doc_orientation_classify,
        "useDocUnwarping": args.use_doc_unwarping,
        "useChartRecognition": args.use_chart_recognition,
    }
    client = PaddleOcrClient(args.job_url, token, args.model, args.poll_interval, args.timeout_seconds)
    artifacts = []
    for source in args.sources:
        job_id = client.submit(source, optional_payload)
        print(f"OCR job submitted: {job_id}")
        data = client.poll(job_id)
        artifact = archive_ocr_result(source, job_id, data)
        artifacts.append(artifact)
        print(f"OCR markdown archived: {artifact.combined_markdown}")

    uploaded = upload_to_maxkb(args, artifacts) if args.upload_to_maxkb else []
    write_index(artifacts, uploaded)
    print(f"OCR result index written: {OCR_RESULT_INDEX}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
