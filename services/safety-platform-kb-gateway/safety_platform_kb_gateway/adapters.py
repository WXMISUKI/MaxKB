# coding=utf-8
"""MaxKB adapter layer."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

import requests

from .config import Settings

TABLE_EXTENSIONS = {".xlsx", ".xls", ".csv"}
SUPPORTED_EXTENSIONS = {
    ".docx", ".doc", ".txt", ".md", ".pdf",
    ".xlsx", ".xls", ".csv",
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
}


class MaxKBError(RuntimeError):
    """Raised when MaxKB returns an application error."""


class MaxKBClient:
    def __init__(self, base_url: str, timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        try:
            payload = response.json()
        except ValueError as exc:
            raise MaxKBError(f"{method} {path} returned non-json response: {response.status_code}") from exc
        if response.status_code >= 400 or payload.get("code") != 200:
            message = payload.get("message") or response.text
            raise MaxKBError(f"{method} {path} failed: {message}")
        return payload.get("data")

    def login(self, username: str, password: str) -> str:
        data = self.request(
            "POST",
            "/user/login",
            json={"username": username, "password": password, "captcha": ""},
        )
        token = data["token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token

    def list_knowledge(self, workspace_id: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/workspace/{workspace_id}/knowledge") or []

    def list_embedding_models(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/workspace/{workspace_id}/model_list", params={"model_type": "EMBEDDING"})
        if isinstance(data, dict):
            return [*data.get("model", []), *data.get("shared_model", [])]
        return data or []

    def create_knowledge_base(
        self,
        workspace_id: str,
        name: str,
        desc: str,
        embedding_model_id: str = "",
    ) -> dict[str, Any]:
        if not embedding_model_id:
            embeddings = self.list_embedding_models(workspace_id)
            if not embeddings:
                raise MaxKBError("No embedding model is available in MaxKB.")
            embedding_model_id = embeddings[0]["id"]
        return self.request(
            "POST",
            f"/workspace/{workspace_id}/knowledge/base",
            json={
                "name": name,
                "folder_id": workspace_id,
                "desc": desc,
                "embedding_model_id": embedding_model_id,
            },
        )

    def delete_knowledge_base(self, workspace_id: str, knowledge_id: str) -> None:
        self.request("DELETE", f"/workspace/{workspace_id}/knowledge/{knowledge_id}")

    def upload_text_document(self, workspace_id: str, knowledge_id: str, file_path: Path) -> list[dict[str, Any]]:
        with file_path.open("rb") as file_obj:
            split_data = self.request(
                "POST",
                f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/split",
                files=[("file", (file_path.name, file_obj, content_type(file_path)))],
                data={"limit": "500", "with_filter": "true"},
            )
        documents = []
        for item in split_data:
            documents.append(
                {
                    "name": truncate_name(item["name"]),
                    "paragraphs": item.get("content", []),
                    "source_file_id": item.get("source_file_id"),
                }
            )
        return self.request(
            "PUT",
            f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/batch_create",
            json=documents,
        )

    def upload_table_document(self, workspace_id: str, knowledge_id: str, file_path: Path) -> Any:
        with file_path.open("rb") as file_obj:
            return self.request(
                "POST",
                f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/table",
                files=[("file", (file_path.name, file_obj, content_type(file_path)))],
            )

    def delete_document(self, workspace_id: str, knowledge_id: str, document_id: str) -> None:
        self.request("DELETE", f"/workspace/{workspace_id}/knowledge/{knowledge_id}/document/{document_id}")

    def hit_test(
        self,
        workspace_id: str,
        knowledge_id: str,
        query_text: str,
        search_mode: str,
        top_number: int,
        similarity: float,
    ) -> list[dict[str, Any]]:
        return self.request(
            "POST",
            f"/workspace/{workspace_id}/knowledge/{knowledge_id}/hit_test",
            json={
                "query_text": query_text,
                "top_number": top_number,
                "similarity": similarity,
                "search_mode": search_mode,
            },
        ) or []


class GatewayAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: MaxKBClient | None = None

    def client(self) -> MaxKBClient:
        if self._client is None:
            self._client = MaxKBClient(self.settings.maxkb_base_url)
            self._client.login(self.settings.maxkb_username, self.settings.maxkb_password)
        return self._client

    def find_team_kb(self, workspace_id: str, team_id: str) -> dict[str, Any] | None:
        prefix = f"team:{team_id}:"
        for item in self.client().list_knowledge(workspace_id):
            if str(item.get("name", "")).startswith(prefix):
                return item
        return None

    def find_knowledge_base(self, workspace_id: str, knowledge_base_id: str) -> dict[str, Any] | None:
        for item in self.client().list_knowledge(workspace_id):
            if str(item.get("id", "")) == knowledge_base_id:
                return item
        return None

    def ensure_team_kb(
        self,
        workspace_id: str,
        team_id: str,
        knowledge_base_id: str = "",
        team_name: str = "",
        project_name: str = "",
        create_if_missing: bool = True,
    ) -> tuple[dict[str, Any], bool]:
        if knowledge_base_id:
            existing = self.find_knowledge_base(workspace_id, knowledge_base_id)
            if existing:
                return existing, False
            raise MaxKBError(f"Knowledge base {knowledge_base_id} was not found.")
        existing = self.find_team_kb(workspace_id, team_id)
        if existing:
            return existing, False
        if not create_if_missing:
            raise MaxKBError(f"Knowledge base for team {team_id} was not found.")
        display_name = team_name or team_id
        name = f"team:{team_id}:{display_name} 资质知识库"
        desc = f"{display_name} 资质资料库"
        if project_name:
            desc = f"{project_name} - {desc}"
        created = self.client().create_knowledge_base(
            workspace_id,
            name,
            desc,
            self.settings.maxkb_default_embedding_model_id,
        )
        return created, True

    def upload_document(self, workspace_id: str, knowledge_id: str, file_path: Path) -> dict[str, Any]:
        suffix = file_path.suffix.lower()
        if suffix in TABLE_EXTENSIONS:
            result = self.client().upload_table_document(workspace_id, knowledge_id, file_path)
            docs = result if isinstance(result, list) else [result] if result else []
        else:
            docs = self.client().upload_text_document(workspace_id, knowledge_id, file_path)
        first = docs[0] if docs else {}
        return {
            "provider_document_id": first.get("id", ""),
            "file_name": file_path.name,
        }

    def delete_document(self, workspace_id: str, knowledge_id: str, document_id: str) -> None:
        self.client().delete_document(workspace_id, knowledge_id, document_id)

    def delete_team_kb(self, workspace_id: str, team_id: str) -> bool:
        existing = self.find_team_kb(workspace_id, team_id)
        if not existing:
            return False
        self.client().delete_knowledge_base(workspace_id, existing["id"])
        return True

    def delete_knowledge_base(self, workspace_id: str, knowledge_base_id: str) -> bool:
        existing = self.find_knowledge_base(workspace_id, knowledge_base_id)
        if not existing:
            return False
        self.client().delete_knowledge_base(workspace_id, knowledge_base_id)
        return True

    def search(
        self,
        workspace_id: str,
        knowledge_id: str,
        query_text: str,
        search_mode: str,
        top_k: int,
        similarity: float,
    ) -> list[dict[str, Any]]:
        hits = self.client().hit_test(workspace_id, knowledge_id, query_text, search_mode, top_k, similarity)
        return [normalize_hit(hit) for hit in hits]


def content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def truncate_name(name: str, limit: int = 128) -> str:
    return name if len(name) <= limit else f"{name[: limit - 10]}...{name[-7:]}"


def is_supported_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def normalize_hit(hit: dict[str, Any]) -> dict[str, Any]:
    document = hit.get("document") if isinstance(hit.get("document"), dict) else {}
    paragraph = hit.get("paragraph") if isinstance(hit.get("paragraph"), dict) else {}
    snippet = str(hit.get("content") or hit.get("text") or paragraph.get("content") or "")
    title = str(hit.get("document_name") or document.get("name") or "")
    return {
        "title": title,
        "snippet": snippet[:500],
        "score": hit.get("similarity") or hit.get("score"),
        "source_type": "",
        "document_id": str(hit.get("document_id") or document.get("id") or ""),
        "paragraph_id": str(hit.get("paragraph_id") or paragraph.get("id") or hit.get("id") or ""),
    }
