from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    state_file: Path
    allowed_source_roots: tuple[Path, ...]
    paddleocr_token: str
    paddleocr_job_url: str
    paddleocr_model: str
    maxkb_base_url: str
    maxkb_username: str
    maxkb_password: str
    maxkb_workspace_id: str
    maxkb_knowledge_name: str
    maxkb_default_knowledge_id: str
    api_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = Path(
            os.getenv("PREFLIGHT_PROJECT_ROOT", Path(__file__).resolve().parents[3])
        ).resolve()
        state_file = Path(
            os.getenv(
                "PREFLIGHT_STATE_FILE",
                project_root / "var" / "preflight-ocr-worker" / "state.json",
            )
        ).resolve()
        roots_value = os.getenv("PREFLIGHT_ALLOWED_SOURCE_ROOTS", str(project_root))
        allowed_roots = tuple(Path(item.strip()).resolve() for item in roots_value.split(os.pathsep) if item.strip())
        return cls(
            project_root=project_root,
            state_file=state_file,
            allowed_source_roots=allowed_roots,
            paddleocr_token=os.getenv("PADDLEOCR_TOKEN", ""),
            paddleocr_job_url=os.getenv(
                "PADDLEOCR_JOB_URL",
                "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            ),
            paddleocr_model=os.getenv("PADDLEOCR_MODEL", "PaddleOCR-VL-1.6"),
            maxkb_base_url=os.getenv("MAXKB_BASE_URL", "http://localhost:8080/admin/api"),
            maxkb_username=os.getenv("MAXKB_USERNAME", "admin"),
            maxkb_password=os.getenv("MAXKB_PASSWORD", ""),
            maxkb_workspace_id=os.getenv("MAXKB_WORKSPACE_ID", "default"),
            maxkb_knowledge_name=os.getenv(
                "MAXKB_KNOWLEDGE_NAME",
                "南江至东岭高速公路改扩建工程 JD-A1 监理审查知识库",
            ),
            maxkb_default_knowledge_id=os.getenv("MAXKB_DEFAULT_KNOWLEDGE_ID", ""),
            api_key=os.getenv("PREFLIGHT_API_KEY", ""),
        )

    def is_allowed_source(self, source: Path) -> bool:
        resolved = source.resolve()
        return any(resolved == root or root in resolved.parents for root in self.allowed_source_roots)
