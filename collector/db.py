"""Database configuration for the Collector backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_SQLITE_URL = "sqlite:///instance/collector.db"
DB_URL = os.getenv("DB_URL", DEFAULT_SQLITE_URL)


def _normalize_sqlite_path(url: str) -> str:
    """Ensure SQLite URLs are expanded to absolute paths and directories exist."""

    if not url.startswith("sqlite"):
        return url

    if url.startswith("sqlite:///"):
        raw_path = url.replace("sqlite:///", "", 1)
    elif url.startswith("sqlite://"):
        # Handles sqlite:// relative paths – treat them as current working directory paths
        raw_path = url.replace("sqlite://", "", 1)
    else:
        return url

    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


_SQLALCHEMY_CONNECT_ARGS: Dict[str, Any] = {}
if DB_URL.startswith("sqlite"):
    DB_URL = _normalize_sqlite_path(DB_URL)
    _SQLALCHEMY_CONNECT_ARGS["check_same_thread"] = False

engine = create_engine(DB_URL, future=True, echo=False, connect_args=_SQLALCHEMY_CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

Base = declarative_base()
