from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


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

    def get(self, ingestion_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read().get(ingestion_id)
            return deepcopy(record) if record else None

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

