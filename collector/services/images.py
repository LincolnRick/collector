"""Helpers related to static image assets for cards."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

IMAGES_DIR = os.getenv("IMAGES_DIR", "cartas_pt_imagens")


def _images_root() -> Path:
    root = Path(IMAGES_DIR)
    if not root.is_absolute():
        root = Path.cwd() / root
    return root


def _candidate_names(set_id: str, number: str) -> Iterable[str]:
    sanitized_set = "".join(ch if ch.isalnum() else "_" for ch in set_id.lower()).strip("_")
    sanitized_number = number.strip().lower().replace("#", "")
    sanitized_number = sanitized_number.replace(" ", "")

    digits = "".join(ch for ch in sanitized_number if ch.isdigit())
    alnum = "".join(ch for ch in sanitized_number if ch.isalnum())

    base_candidates = {sanitized_number}
    if digits:
        base_candidates.add(digits)
        base_candidates.add(digits.zfill(3))
        base_candidates.add(digits.zfill(4))
    if alnum:
        base_candidates.add(alnum)

    for candidate in base_candidates:
        yield f"{sanitized_set}_{candidate}"
        yield f"{sanitized_set}{candidate}"
        yield candidate


def _guess_local_image(set_id: str | None, number: str | None) -> Optional[str]:
    """Return a relative path to an image in ``IMAGES_DIR`` if it exists."""

    if not set_id or not number:
        return None

    root = _images_root()
    if not root.exists():
        return None

    extensions = (".png", ".jpg", ".jpeg", ".webp")
    for candidate in _candidate_names(set_id, number):
        for ext in extensions:
            path = root / f"{candidate}{ext}"
            if path.exists():
                try:
                    relative = path.relative_to(root)
                except ValueError:
                    relative = path
                return relative.as_posix()
    return None


def guess_local_image(set_id: str | None, number: str | None) -> Optional[str]:
    """Public wrapper around :func:`_guess_local_image` used by services."""

    return _guess_local_image(set_id, number)
