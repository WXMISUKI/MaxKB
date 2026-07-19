# coding=utf-8
"""
Local MaxKB integration helper for the construction-supervision pilot dataset.

The script intentionally reads secrets from environment variables and never writes
them to result artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("Missing dependency: requests. Please run this in an environment with requests installed.") from exc


DEFAULT_BASE_URL = "http://localhost:8080/admin/api"
DEFAULT_WORKSPACE_ID = "default"
DEFAULT_KNOWLEDGE_NAME = "南江至东岭高速公路改扩建工程 JD-A1 监理审查知识库"
DEFAULT_KNOWLEDGE_DESC = (
    "用于验证 LJ-01 路基土石方分包作业队开工条件审查和 "
    "K12+000-K18+500 路基填筑施工方案审查。"
)
DEFAULT_MODEL_NAME = "Mimo TokenPlan mimo-v2.5-pro"
DEFAULT_MODEL_ID = "mimo-v2.5-pro"
DEFAULT_API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
PILOT_ROOT = Path(__file__).resolve().parents[2] / "simulated-pilot-dataset" / "NJDL-JD-A1"
UPLOAD_PLAN = PILOT_ROOT / "00_manifest" / "maxkb-upload-plan.csv"
UPLOAD_RESULT = PILOT_ROOT / "00_manifest" / "maxkb-upload-result.csv"


class MaxKBError(RuntimeError):
    pass


@dataclass
class UploadRow:
    upload_order: str
    upload_group: str
    document_id: str
    relative_path: str
    file_format: str
    document_type: str
    review_task_id: str

    @property
    def path(self) -> Path:
        return PILOT_ROOT / self.relative_path


class MaxKBClient:
    def __init__(self, base_url: str, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise MaxKBError(f"{method} {path} returned non-json response: {response.status_code}") from exc
        if response.status_code >= 400 or payload.get("code") != 200:
            message = payload.get("message") or response.text
            raise MaxKBError(f"{method} {path} failed: {message}")
        return payload.get("data")

    def login(self, username: str, password: str) -> str:
        captcha = self._get_cached_captcha(username) or ""
        try:
            data = self.request(
                "POST",
                "/user/login",
                json={"username": username, "password": password, "captcha": captcha},
            )
        except MaxKBError:
            captcha = self._refresh_captcha_from_server(username)
            data = self.request(
                "POST",
                "/user/login",
                json={"username": username, "password": password, "captcha": captcha},
            )
        token = data["token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token

    def _refresh_captcha_from_server(self, username: str) -> str:
        self.request("GET", "/user/captcha", params={"username": username})
        captcha = self._get_cached_captcha(username)
        if not captcha:
            raise MaxKBError("Captcha is required but could not be read from local Redis.")
        return captcha

    @staticmethod
    def _get_cached_captcha(username: str) -> str | None:
        if os.name != "nt":
            return None
        command = (
            "docker exec maxkb sh -lc "
            f"\"redis-cli -a Password123@redis --no-auth-warning get ':CAPTCHA:system_{username}'\""
        )
        output = os.popen(command).read()
        match = re.search(r"([a-z0-9]{4})", output)
        return match.group(1) if match else None

    def list_models(self, workspace_id: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/workspace/{workspace_id}/model") or []

    def ensure_openai_llm(
        self,
        workspace_id: str,
        display_name: str,
        model_name: str,
        api_base: str,
        api_key: str,
    ) -> dict[str, Any]:
        for model in self.list_models(workspace_id):
            if model.get("name") == display_name:
                return model
        params_form = self.request(
            "GET",
            "/provider/model_params_form",
            params={
                "provider": "model_openai_provider",
                "model_type": "LLM",
                "model_name": model_name,
            },
        )
        return self.request(
            "POST",
            f"/workspace/{workspace_id}/model",
            json={
                "name": display_name,
                "provider": "model_openai_provider",
                "model_type": "LLM",
                "model_name": model_name,
                "credential": {"api_base": api_base, "api_key": api_key},
                "model_params_form": params_form,
            },
        )

    def list_knowledge(self, workspace_id: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/workspace/{workspace_id}/knowledge") or []

    def list_embedding_models(self, workspace_id: str) -> list[dict[str, Any]]:
        models = self.request("GET", f"/workspace/{workspace_id}/model_list", params={"model_type": "EMBEDDING"})
        if isinstance(models, dict):
            return [*models.get("model", []), *models.get("shared_model", [])]
        return models or []

    def ensure_knowledge(self, workspace_id: str, name: str, desc: str) -> dict[str, Any]:
        for knowledge in self.list_knowledge(workspace_id):
            if knowledge.get("name") == name:
                return knowledge
        embeddings = self.list_embedding_models(workspace_id)
        if not embeddings:
            raise MaxKBError("No embedding model is available. Create or enable an embedding model first.")
        return self.request(
            "POST",
            f"/workspace/{workspace_id}/knowledge/base",
            json={
                "name": name,
                "folder_id": workspace_id,
                "desc": desc,
                "embedding_model_id": embeddings[0]["id"],
            },
        )

    def upload_text_document(self, workspace_id: str, knowledge_id: str, file_path: Path) -> Any:
        with file_path.open("rb") as file:
            split_data = self.request(
                "POST",
                f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/split",
                files=[("file", (file_path.name, file, _content_type(file_path)))],
                data={"limit": "500", "with_filter": "true"},
            )
        documents = []
        for item in split_data:
            documents.append(
                {
                    "name": _truncate_name(item["name"]),
                    "paragraphs": item.get("content", []),
                    "source_file_id": item.get("source_file_id"),
                }
            )
        return self.request(
            "PUT",
            f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/batch_create",
            json=documents,
        )

    def upload_table_documents(self, workspace_id: str, knowledge_id: str, file_paths: list[Path]) -> Any:
        opened = []
        try:
            for path in file_paths:
                opened.append(("file", (path.name, path.open("rb"), _content_type(path))))
            return self.request(
                "POST",
                f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/table",
                files=opened,
            )
        finally:
            for _, (_, file_obj, _) in opened:
                file_obj.close()


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream"


def _truncate_name(name: str, limit: int = 128) -> str:
    return name if len(name) <= limit else f"{name[: limit - 10]}...{name[-7:]}"


def read_upload_plan(plan_path: Path) -> list[UploadRow]:
    with plan_path.open("r", encoding="utf-8-sig", newline="") as file:
        return [UploadRow(**row) for row in csv.DictReader(file)]


def write_result(rows: list[dict[str, str]]) -> None:
    UPLOAD_RESULT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "upload_order",
        "document_id",
        "relative_path",
        "file_format",
        "api_route_type",
        "status",
        "message",
    ]
    with UPLOAD_RESULT.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure local MaxKB and upload the pilot dataset.")
    parser.add_argument("--base-url", default=os.getenv("MAXKB_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--workspace-id", default=os.getenv("MAXKB_WORKSPACE_ID", DEFAULT_WORKSPACE_ID))
    parser.add_argument("--username", default=os.getenv("MAXKB_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("MAXKB_PASSWORD", "Admin123@"))
    parser.add_argument("--knowledge-name", default=os.getenv("MAXKB_KNOWLEDGE_NAME", DEFAULT_KNOWLEDGE_NAME))
    parser.add_argument("--knowledge-desc", default=DEFAULT_KNOWLEDGE_DESC)
    parser.add_argument("--mimo-api-base", default=os.getenv("MIMO_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--mimo-model", default=os.getenv("MIMO_MODEL", DEFAULT_MODEL_ID))
    parser.add_argument("--mimo-display-name", default=os.getenv("MIMO_DISPLAY_NAME", DEFAULT_MODEL_NAME))
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = MaxKBClient(args.base_url)
    client.login(args.username, args.password)

    if not args.skip_model:
        api_key = os.getenv("MIMO_API_KEY")
        if not api_key:
            raise MaxKBError("MIMO_API_KEY is required unless --skip-model is used.")
        model = client.ensure_openai_llm(
            args.workspace_id,
            args.mimo_display_name,
            args.mimo_model,
            args.mimo_api_base,
            api_key,
        )
        print(f"LLM ready: {model.get('name')} ({model.get('id')})")

    knowledge = client.ensure_knowledge(args.workspace_id, args.knowledge_name, args.knowledge_desc)
    knowledge_id = knowledge["id"]
    print(f"Knowledge ready: {knowledge.get('name')} ({knowledge_id})")

    if args.skip_upload:
        return 0

    rows = read_upload_plan(UPLOAD_PLAN)
    results: list[dict[str, str]] = []
    table_rows = [row for row in rows if row.file_format.lower() == "xlsx"]

    for row in [item for item in rows if item.file_format.lower() in {"docx", "pdf"}]:
        try:
            client.upload_text_document(args.workspace_id, knowledge_id, row.path)
            results.append(_result_row(row, "split+batch_create", "success", ""))
            print(f"Uploaded text document: {row.relative_path}")
        except Exception as exc:
            results.append(_result_row(row, "split+batch_create", "failed", str(exc)))
            write_result(results)
            raise

    if table_rows:
        try:
            client.upload_table_documents(args.workspace_id, knowledge_id, [row.path for row in table_rows])
            for row in table_rows:
                results.append(_result_row(row, "table", "success", ""))
            print(f"Uploaded table files: {len(table_rows)}")
        except Exception as exc:
            for row in table_rows:
                results.append(_result_row(row, "table", "failed", str(exc)))
            write_result(results)
            raise

    write_result(results)
    print(f"Upload result written: {UPLOAD_RESULT}")
    return 0


def _result_row(row: UploadRow, api_route_type: str, status: str, message: str) -> dict[str, str]:
    return {
        "upload_order": row.upload_order,
        "document_id": row.document_id,
        "relative_path": row.relative_path,
        "file_format": row.file_format,
        "api_route_type": api_route_type,
        "status": status,
        "message": message,
    }


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        time.sleep(0.1)
        raise SystemExit(1)
