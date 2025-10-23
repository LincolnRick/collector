from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.services import images


def test_resolve_image_reference_with_relative_path(tmp_path, monkeypatch):
    images_dir = tmp_path / "assets"
    images_dir.mkdir()

    file_path = images_dir / "pikachu.png"
    file_path.write_bytes(b"")

    monkeypatch.setattr(images, "IMAGES_DIR", str(images_dir))

    resolved = images.resolve_image_reference("pikachu.png")
    assert resolved == "pikachu.png"


def test_resolve_image_reference_without_extension(tmp_path, monkeypatch):
    images_dir = tmp_path / "assets"
    images_dir.mkdir()

    file_path = images_dir / "charmander.jpg"
    file_path.write_bytes(b"")

    monkeypatch.setattr(images, "IMAGES_DIR", str(images_dir))

    resolved = images.resolve_image_reference("charmander")
    assert resolved == "charmander.jpg"
