"""Application settings, read from environment variables with safe defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# backend/app/config.py: parents[1] is backend/, parents[2] is the repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    agents_config_path: Path
    execution_timeout_seconds: float
    max_task_bytes: int
    allowed_origins: tuple
    database_path: Path  # SQLite file for traces, evaluations and failures


def get_settings() -> Settings:
    origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        data_dir=Path(os.getenv("DATA_DIR", REPO_ROOT / "data")),
        agents_config_path=Path(os.getenv("AGENTS_CONFIG", BACKEND_DIR / "agents.yaml")),
        execution_timeout_seconds=float(os.getenv("EXECUTION_TIMEOUT_SECONDS", "30")),
        max_task_bytes=int(os.getenv("MAX_TASK_BYTES", "100000")),
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        database_path=Path(os.getenv("DATABASE_PATH", BACKEND_DIR / "review.db")),
    )
