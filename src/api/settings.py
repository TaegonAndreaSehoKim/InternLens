from __future__ import annotations

import os
from pathlib import Path
from typing import List


DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
DEFAULT_JOBS_DIR = "data/processed/jobs"


def env_list(name: str, default: List[str]) -> List[str]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def env_value(name: str, default: str) -> str:
    raw_value = os.getenv(name, "")
    return raw_value.strip() or default


def resolve_project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path
