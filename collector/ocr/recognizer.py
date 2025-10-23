"""Placeholder module for OCR capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image


class OCRRecognizer:
    """Simple OCR recognizer wrapper using Tesseract."""

    def __init__(self, language: str = "eng") -> None:
        self.language = language

    def extract_text(self, image_path: Path) -> Optional[str]:
        """Extract text from the provided image path if possible."""

        try:
            with Image.open(image_path) as img:
                return pytesseract.image_to_string(img, lang=self.language)
        except FileNotFoundError:
            return None
        except OSError:
            return None
