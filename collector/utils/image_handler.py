"""Image loading and processing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image


def load_image(path: Path) -> Optional[Image.Image]:
    """Load an image from disk if available."""

    try:
        with Image.open(path) as img:
            return img.copy()
    except FileNotFoundError:
        return None
    except OSError:
        return None


def save_image_copy(image: Image.Image, destination: Path) -> None:
    """Persist an image copy to the destination path."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
