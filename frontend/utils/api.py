"""Utilitários para comunicação com o backend FastAPI."""

from __future__ import annotations

import json
import os
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()


class CollectorAPIError(RuntimeError):
    """Erro genérico ao comunicar com a Collector API."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class CollectorAPIClient:
    """Cliente HTTP simples para a Collector API."""

    base_url: str = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
    timeout: float = float(os.getenv("FASTAPI_TIMEOUT", "10"))

    def _build_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _handle_response(self, response: requests.Response) -> Any:
        if response.ok:
            if response.content:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return response.json()
                return response.text
            return None

        detail = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload
        except json.JSONDecodeError:
            detail = response.text

        message = detail or f"Erro na requisição (status {response.status_code})"
        raise CollectorAPIError(message, status_code=response.status_code)

    def healthcheck(self) -> bool:
        try:
            payload = self._request("GET", "/health")
        except CollectorAPIError:
            return False
        return isinstance(payload, dict) and payload.get("status") == "ok"

    def list_cards(self) -> List[Dict[str, Any]]:
        payload = self._request("GET", "/cards")
        return list(payload or [])

    def create_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._request("POST", "/cards", json=card)
        return dict(payload or {})

    def bulk_create(self, cards: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        created: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for index, card in enumerate(cards):
            try:
                created.append(self.create_card(card))
            except CollectorAPIError as exc:  # pragma: no cover - feedback ao usuário
                errors.append({"index": index, "error": str(exc)})
        return created, errors

    def update_card(self, card_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self._request("PATCH", f"/cards/{card_id}", json=payload)
        return dict(response or {})

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._build_url(path)
        response = requests.request(method, url, timeout=self.timeout, **kwargs)
        return self._handle_response(response)


_client = CollectorAPIClient()


def get_client() -> CollectorAPIClient:
    """Retorna uma instância reutilizável do cliente da API."""

    return _client


def parse_card_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Converte dados crus (ex.: CSV) para o formato aceito pela API."""

    def _normalize_key(key: str) -> str:
        normalized = unicodedata.normalize("NFKD", key)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = normalized.lower().strip()
        for token in (" ", "-", "/"):
            normalized = normalized.replace(token, "_")
        return normalized

    def _parse_bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        text = str(value).strip().lower()
        if text in {"", "nao", "não", "false", "0", "no", "n"}:
            return False
        if text in {"sim", "yes", "true", "1", "possuo", "tenho"}:
            return True
        return None

    field_aliases = {
        "nome": "nome",
        "name": "nome",
        "hp": "hp",
        "tipo": "tipo",
        "type": "tipo",
        "raridade": "raridade",
        "rarity": "raridade",
        "set": "set",
        "conjunto": "set",
        "set_id": "set_id",
        "numero": "numero",
        "número": "numero",
        "number": "numero",
        "artista": "artista",
        "artist": "artista",
        "habilidade": "habilidade_nome",
        "habilidade_nome": "habilidade_nome",
        "ability": "habilidade_nome",
        "texto_da_habilidade": "habilidade_desc",
        "habilidade_texto": "habilidade_desc",
        "ability_text": "habilidade_desc",
        "ataques": "ataques",
        "attacks": "ataques",
        "fraquezas": "fraquezas",
        "fraqueza": "fraquezas",
        "weaknesses": "fraquezas",
        "resistencias": "resistencias",
        "resistências": "resistencias",
        "resistances": "resistencias",
        "recuo": "recuo",
        "retreat": "recuo",
        "retreat_cost": "recuo",
        "imagem": "imagem",
        "imagem_arquivo": "imagem",
        "image": "imagem",
        "image_url": "imagem",
        "possui": "possui",
        "tem": "possui",
        "tenho": "possui",
    }

    payload: Dict[str, Any] = {}
    for key, value in raw.items():
        if key is None:
            continue
        normalized_key = _normalize_key(str(key))
        canonical_key = field_aliases.get(normalized_key)
        if not canonical_key:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue

        if canonical_key == "hp":
            digits = "".join(ch for ch in str(value) if ch.isdigit())
            payload[canonical_key] = digits or str(value)
            continue

        if canonical_key == "possui":
            parsed_bool = _parse_bool(value)
            if parsed_bool is not None:
                payload[canonical_key] = parsed_bool
            continue

        payload[canonical_key] = value

    return payload

