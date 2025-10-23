"""Utilitários para comunicação com o backend FastAPI."""

from __future__ import annotations

import json
import os
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

    def _parse_json_or_split(value: Optional[str]) -> Optional[Any]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return [item.strip() for item in value.split("|") if item.strip()]

    payload: Dict[str, Any] = {}
    for key, value in raw.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue
        payload[key] = value

    if "hp" in payload:
        try:
            payload["hp"] = int(payload["hp"])
        except (TypeError, ValueError):
            payload.pop("hp", None)

    list_fields = {"attacks", "weaknesses", "resistances", "retreat_cost"}
    for field in list_fields:
        if field in raw:
            parsed = _parse_json_or_split(raw.get(field))
            if parsed is not None:
                payload[field] = parsed

    if "for_trade" in payload:
        value = str(payload["for_trade"]).strip().lower()
        payload["for_trade"] = value in {"1", "true", "yes", "sim"}

    # compatibilidade com o modelo Pydantic (alias "type")
    if "type" not in payload and "card_type" in payload:
        payload["type"] = payload.pop("card_type")

    return payload

