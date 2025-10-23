"""CSV importer that populates the database with card data."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional

import chardet

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Card
from .images import guess_local_image, resolve_image_reference


def _parse_list(value: Optional[str]) -> Optional[list[str]]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in value.split("|") if item.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return None


def _parse_attacks(row: Dict[str, Any]) -> Optional[str]:
    attacks: Dict[str, Dict[str, Any]] = {}
    for key, raw_value in row.items():
        if not isinstance(key, str) or not key.startswith("attacks_"):
            continue
        if raw_value in (None, ""):
            continue
        parts = key.split("_", 2)
        if len(parts) != 3:
            continue
        _, index, attribute = parts
        payload = attacks.setdefault(index, {})
        payload[attribute] = raw_value
    if not attacks:
        return None
    ordered = [payload for _, payload in sorted(attacks.items(), key=lambda item: item[0])]
    return json.dumps(ordered, ensure_ascii=False)


def _prepare_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        payload[key.strip()] = value
    return payload


def detect_encoding(path: Path) -> str:
    with path.open("rb") as buffer:
        raw = buffer.read(4096)
    guess = chardet.detect(raw)
    encoding = guess.get("encoding", "utf-8")
    print(f"[INFO] Detected encoding: {encoding}")
    return encoding or "utf-8"


def _open_csv(csv_path: Path, encoding: str):
    try:
        return csv_path.open("r", encoding=encoding, newline="")
    except UnicodeDecodeError:
        print("[WARN] Fallback para latin1 devido a erro de decodificação.")
        return csv_path.open("r", encoding="latin1", newline="")


def _prepare_reader(handle):
    sample = handle.read(2048)
    handle.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        handle.seek(0)
        return csv.DictReader(handle, dialect=dialect)
    except csv.Error:
        handle.seek(0)
        return csv.DictReader(handle)


def import_csv(path: str) -> Dict[str, Any]:
    """Import cards from a CSV file located at ``path``.

    Returns a dictionary with counters detailing how many rows were created, updated
    or skipped, in addition to a list of errors.
    """

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    stats: Dict[str, Any] = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    encoding = detect_encoding(csv_path)
    with _open_csv(csv_path, encoding) as handle:
        reader = _prepare_reader(handle)
        session: Session = SessionLocal()
        try:
            for index, row in enumerate(reader, start=1):
                payload = _prepare_payload(row)
                set_id = payload.get("set_id") or payload.get("setId")
                number = payload.get("number") or payload.get("card_number")
                if not set_id or not number:
                    stats["skipped"] += 1
                    stats["errors"].append(
                        {"row": index, "error": "Missing set_id or number"}
                    )
                    continue

                card: Optional[Card] = (
                    session.query(Card).filter(Card.set_id == set_id, Card.number == number).one_or_none()
                )
                is_new = card is None
                if card is None:
                    card = Card(set_id=set_id, number=number)

                if is_new and not payload.get("name"):
                    stats["skipped"] += 1
                    stats["errors"].append({"row": index, "error": "Missing name"})
                    continue

                if "name" in payload and payload["name"]:
                    card.name = payload["name"]

                hp_value = payload.get("hp") or payload.get("hp_str")
                if hp_value is not None:
                    card.hp = str(hp_value)

                types_source = payload.get("types") or payload.get("type")
                if types_source is not None:
                    types = _parse_list(str(types_source)) or []
                    card.types = json.dumps(types, ensure_ascii=False)

                if "rarity" in payload:
                    card.rarity = payload.get("rarity")
                if "set_name" in payload or "set" in payload:
                    card.set_name = payload.get("set_name") or payload.get("set")
                if "artist" in payload:
                    card.artist = payload.get("artist")
                if "ability_name" in payload or "abilities_0_name" in payload:
                    card.ability_name = payload.get("ability_name") or payload.get("abilities_0_name")
                if "ability_text" in payload or "abilities_0_text" in payload:
                    card.ability_text = payload.get("ability_text") or payload.get("abilities_0_text")

                if "weaknesses" in payload:
                    weaknesses = _parse_list(payload.get("weaknesses")) or []
                    card.weaknesses = json.dumps(weaknesses, ensure_ascii=False)
                if "resistances" in payload:
                    resistances = _parse_list(payload.get("resistances")) or []
                    card.resistances = json.dumps(resistances, ensure_ascii=False)
                retreat_source = payload.get("retreat_cost") or payload.get("retreat")
                if retreat_source is not None:
                    retreat = _parse_list(str(retreat_source)) or []
                    card.retreat_cost = json.dumps(retreat, ensure_ascii=False)
                attacks_payload = _parse_attacks(payload)
                card.attacks = attacks_payload
                if "image_url" in payload or "images_small" in payload:
                    card.image_url = payload.get("image_url") or payload.get("images_small")

                local_image = payload.get("image_path")
                if not local_image:
                    pt_image = payload.get("Imagem") or payload.get("imagem")
                    local_image = resolve_image_reference(pt_image)
                if not local_image:
                    local_image = guess_local_image(set_id, number)
                if local_image:
                    card.image_path = local_image

                session.add(card)
                try:
                    session.flush()
                except IntegrityError as exc:
                    session.rollback()
                    stats["errors"].append({"row": index, "error": str(exc.orig) if exc.orig else str(exc)})
                    stats["skipped"] += 1
                    continue

                stats["created" if is_new else "updated"] += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    return stats


__all__ = ["import_csv"]
