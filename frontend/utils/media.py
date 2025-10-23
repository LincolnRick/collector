"""Utilitários auxiliares para trabalhar com imagens das cartas."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterator, List, Optional

_DEFAULT_DIRECTORIES: List[Path] = []
_ENV_DIR = os.getenv("CARD_IMAGES_DIR")
if _ENV_DIR:
    _DEFAULT_DIRECTORIES.append(Path(_ENV_DIR))

_DEFAULT_DIRECTORIES.extend(
    [
        Path.cwd() / "images",
        Path.cwd() / "data" / "images",
        Path(__file__).resolve().parents[2] / "images",
        Path(__file__).resolve().parents[2] / "data" / "images",
    ]
)


@lru_cache()
def _existing_directories() -> tuple[Path, ...]:
    directories: List[Path] = []
    for directory in _DEFAULT_DIRECTORIES:
        if directory is None:
            continue
        try:
            resolved = directory.expanduser().resolve()
        except FileNotFoundError:
            continue
        if resolved.exists() and resolved.is_dir():
            directories.append(resolved)
    return tuple(directories)


def iter_image_candidates(filename: str) -> Iterator[Path]:
    """Itera sobre caminhos possíveis para localizar uma imagem."""

    for directory in _existing_directories():
        yield directory / filename


def resolve_card_image(filename: Optional[str]) -> Optional[str]:
    """Retorna o caminho absoluto da imagem da carta, se disponível."""

    if not filename:
        return None

    for candidate in iter_image_candidates(str(filename)):
        if candidate.exists() and candidate.is_file():
            return candidate.as_posix()
    return None
