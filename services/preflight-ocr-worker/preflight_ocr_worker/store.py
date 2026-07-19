from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


class IdempotencyConflict(RuntimeError):
    pass


class JsonStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            payload[record["ingestion_id"]] = deepcopy(record)
            self._write(payload)
            return deepcopy(record)

    def create_idempotent(self, record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        with self._lock:
            payload = self._read()
            for existing in payload.values():
                if existing.get("idempotency_key") != record["idempotency_key"]:
                    continue
                if existing.get("request_fingerprint") != record["request_fingerprint"]:
                    raise IdempotencyConflict("Idempotency key was already used for a different request.")
                return deepcopy(existing), False
            payload[record["ingestion_id"]] = deepcopy(record)
            self._write(payload)
            return deepcopy(record), True

    def get(self, ingestion_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read().get(ingestion_id)
            return deepcopy(record) if record else None

    def get_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        with self._lock:
            for record in self._read().values():
                if record.get("idempotency_key") == idempotency_key:
                    return deepcopy(record)
            return None

    def update(self, ingestion_id: str, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            if ingestion_id not in payload:
                raise KeyError(ingestion_id)
            payload[ingestion_id].update(deepcopy(values))
            self._write(payload)
            return deepcopy(payload[ingestion_id])

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.path)
