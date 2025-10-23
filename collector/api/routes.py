"""FastAPI application exposing Collector backend routes."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import Base, SessionLocal, engine
from ..models import Card, CollectionItem
from ..services import importer
from ..services.images import IMAGES_DIR

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Collector API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

images_root = Path(IMAGES_DIR)
if not images_root.is_absolute():
    images_root = Path.cwd() / images_root
images_root.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_root), name="images")


class AttackOut(BaseModel):
    """Represents a simplified attack payload returned to the frontend."""

    name: Optional[str] = None
    cost: List[str] = Field(default_factory=list)
    damage: Optional[str] = None
    text: Optional[str] = None


class PriceOut(BaseModel):
    """Serialized representation of :class:`collector.models.PriceQuote`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    currency: Optional[str] = None
    avg_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    url: Optional[str] = None
    fetched_at: datetime


class CardOut(BaseModel):
    """Serialized representation of :class:`collector.models.Card`."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    hp: Optional[str] = None
    types: List[str] = Field(default_factory=list)
    primary_type: Optional[str] = Field(default=None, alias="type")
    rarity: Optional[str] = None
    set_name: Optional[str] = None
    set_id: str
    number: str
    artist: Optional[str] = None
    ability_name: Optional[str] = None
    ability_text: Optional[str] = None
    attacks: List[AttackOut] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    resistances: List[str] = Field(default_factory=list)
    retreat_cost: List[str] = Field(default_factory=list)
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    for_trade: bool = False
    price_quotes: List[PriceOut] = Field(default_factory=list)


class CardCreatePayload(BaseModel):
    """Payload recebido na criação de cartas via API legada (em português)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome: str = Field(..., min_length=1)
    set_id: str = Field(..., min_length=1)
    numero: str = Field(..., min_length=1)
    hp: Optional[str] = None
    tipo: Optional[str] = None
    raridade: Optional[str] = None
    set: Optional[str] = None
    artista: Optional[str] = None
    habilidade_nome: Optional[str] = None
    habilidade_desc: Optional[str] = None
    ataques: Optional[Any] = None
    fraquezas: Optional[Any] = None
    resistencias: Optional[Any] = None
    recuo: Optional[Any] = None
    imagem: Optional[str] = None
    possui: bool = False


class CardUpdatePayload(BaseModel):
    """Payload utilizado para atualizar campos das cartas existentes."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome: Optional[str] = Field(default=None, min_length=1)
    set_id: Optional[str] = Field(default=None, min_length=1)
    numero: Optional[str] = Field(default=None, min_length=1)
    hp: Optional[str] = None
    tipo: Optional[str] = None
    raridade: Optional[str] = None
    set: Optional[str] = None
    artista: Optional[str] = None
    habilidade_nome: Optional[str] = None
    habilidade_desc: Optional[str] = None
    ataques: Optional[Any] = None
    fraquezas: Optional[Any] = None
    resistencias: Optional[Any] = None
    recuo: Optional[Any] = None
    imagem: Optional[str] = None
    possui: Optional[bool] = None


class CardOutPT(BaseModel):
    """Representação compatível com o frontend Streamlit (campos em português)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    hp: Optional[str] = None
    tipo: Optional[str] = None
    raridade: Optional[str] = None
    set: Optional[str] = None
    set_id: str
    numero: str
    artista: Optional[str] = None
    habilidade_nome: Optional[str] = None
    habilidade_desc: Optional[str] = None
    ataques: Optional[str] = None
    fraquezas: Optional[str] = None
    resistencias: Optional[str] = None
    recuo: Optional[str] = None
    imagem: Optional[str] = None
    possui: bool = False


class CollectionCreate(BaseModel):
    """Payload used to create items in the user's collection."""

    card_id: int
    quantity: int = Field(1, ge=1)
    condition: Optional[str] = None
    for_trade: bool = False
    notes: Optional[str] = None


class CollectionOut(BaseModel):
    """Representation of :class:`collector.models.CollectionItem`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    quantity: int
    condition: Optional[str] = None
    for_trade: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    card: Optional[CardOutPT] = None


class ImportResult(BaseModel):
    """Response returned by the CSV importer endpoint."""

    created: int
    updated: int
    skipped: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)


async def _save_uploaded_file(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "cards.csv").suffix or ".csv"
    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    tmp_path = Path(tmp_name)
    data = await upload.read()
    tmp_path.write_bytes(data)
    return tmp_path


def get_db() -> Iterable[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_json_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = value
    if isinstance(payload, list):
        return [str(item) for item in payload]
    if isinstance(payload, str):
        return [item.strip() for item in payload.split("|") if item.strip()]
    return []


def _load_attacks(value: Optional[str]) -> List[AttackOut]:
    if not value:
        return []
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        return []
    attacks: List[AttackOut] = []
    if not isinstance(raw, list):
        return attacks
    for attack in raw:
        if not isinstance(attack, dict):
            continue
        cost_raw = attack.get("cost")
        cost: List[str]
        if isinstance(cost_raw, list):
            cost = [str(item) for item in cost_raw]
        elif isinstance(cost_raw, str):
            cost = [item.strip() for item in cost_raw.split("|") if item.strip()]
        else:
            cost = []
        attacks.append(
            AttackOut(
                name=attack.get("name"),
                cost=cost,
                damage=attack.get("damage"),
                text=attack.get("text"),
            )
        )
    return attacks


def _card_to_schema(card: Card) -> CardOut:
    types = _load_json_list(card.types)
    card_schema = CardOut(
        id=card.id,
        name=card.name,
        hp=card.hp,
        types=types,
        primary_type=types[0] if types else None,
        rarity=card.rarity,
        set_name=card.set_name,
        set_id=card.set_id,
        number=card.number,
        artist=card.artist,
        ability_name=card.ability_name,
        ability_text=card.ability_text,
        attacks=_load_attacks(card.attacks),
        weaknesses=_load_json_list(card.weaknesses),
        resistances=_load_json_list(card.resistances),
        retreat_cost=_load_json_list(card.retreat_cost),
        image_path=card.image_path,
        image_url=card.image_url,
        created_at=card.created_at,
        updated_at=card.updated_at,
        for_trade=any(item.for_trade for item in card.collection_items),
        price_quotes=[PriceOut.model_validate(price) for price in card.price_quotes],
    )
    return card_schema


def _fetch_card(db: Session, card_id: int) -> Optional[Card]:
    return (
        db.execute(
            select(Card)
            .options(selectinload(Card.collection_items), selectinload(Card.price_quotes))
            .where(Card.id == card_id)
        )
        .scalars()
        .first()
    )


def _normalize_optional_str(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_list_payload(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            tokens = [token.strip() for token in text.replace(",", "|").split("|") if token.strip()]
            items = tokens
        else:
            if isinstance(parsed, list):
                items = [str(item).strip() for item in parsed if str(item).strip()]
            elif isinstance(parsed, str):
                items = [parsed.strip()] if parsed.strip() else []
            else:
                items = [str(parsed).strip()] if str(parsed).strip() else []
    if not items:
        return None
    return json.dumps(items, ensure_ascii=False)


def _list_to_text(value: Optional[str]) -> Optional[str]:
    items = _load_json_list(value)
    if not items:
        return None
    return " | ".join(items)


def _normalize_attacks_payload(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text or None


def _attacks_to_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(data, list):
        summaries: List[str] = []
        for attack in data:
            if not isinstance(attack, dict):
                continue
            name = str(attack.get("name") or "").strip()
            damage = str(attack.get("damage") or "").strip()
            text = str(attack.get("text") or "").strip()
            parts: List[str] = []
            if name:
                parts.append(name)
            if damage:
                parts.append(f"Dano: {damage}")
            if text:
                parts.append(text)
            if parts:
                summaries.append(" - ".join(parts))
        if summaries:
            return " | ".join(summaries)
        return None
    return value


def _apply_card_payload(card: Card, payload: Dict[str, Any]) -> None:
    mapping = {
        "nome": "name",
        "hp": "hp",
        "tipo": "types",
        "raridade": "rarity",
        "set": "set_name",
        "set_id": "set_id",
        "numero": "number",
        "artista": "artist",
        "habilidade_nome": "ability_name",
        "habilidade_desc": "ability_text",
        "ataques": "attacks",
        "fraquezas": "weaknesses",
        "resistencias": "resistances",
        "recuo": "retreat_cost",
    }
    for field, value in payload.items():
        if field not in mapping:
            continue
        if field in {"fraquezas", "resistencias", "recuo"}:
            normalized = _normalize_list_payload(value)
        elif field == "tipo":
            normalized = _normalize_list_payload(value)
        elif field == "ataques":
            normalized = _normalize_attacks_payload(value)
        else:
            normalized = _normalize_optional_str(value)
        setattr(card, mapping[field], normalized)
    image_value = payload.get("imagem")
    if image_value is not None:
        normalized_image = _normalize_optional_str(image_value)
        if normalized_image and normalized_image.lower().startswith("http"):
            card.image_url = normalized_image
            card.image_path = None
        else:
            card.image_path = normalized_image
            card.image_url = None


def _card_to_pt_schema(card: Card) -> CardOutPT:
    types = _load_json_list(card.types)
    weaknesses = _list_to_text(card.weaknesses)
    resistances = _list_to_text(card.resistances)
    retreat = _list_to_text(card.retreat_cost)
    image = card.image_path or card.image_url
    possui = any(item.quantity > 0 for item in card.collection_items)
    return CardOutPT(
        id=card.id,
        nome=card.name,
        hp=card.hp,
        tipo=types[0] if types else None,
        raridade=card.rarity,
        set=card.set_name,
        set_id=card.set_id,
        numero=card.number,
        artista=card.artist,
        habilidade_nome=card.ability_name,
        habilidade_desc=card.ability_text,
        ataques=_attacks_to_text(card.attacks),
        fraquezas=weaknesses,
        resistencias=resistances,
        recuo=retreat,
        imagem=image,
        possui=possui,
    )


def _collection_to_schema(item: CollectionItem) -> CollectionOut:
    return CollectionOut(
        id=item.id,
        card_id=item.card_id,
        quantity=item.quantity,
        condition=item.condition,
        for_trade=item.for_trade,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
        card=_card_to_pt_schema(item.card) if item.card else None,
    )


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/import/csv", response_model=ImportResult)
async def import_csv_endpoint(
    csv_file: UploadFile | None = File(default=None),
    csv_path: str | None = Form(default=None),
) -> ImportResult:
    if csv_file is None and not csv_path:
        raise HTTPException(status_code=400, detail="csv_file or csv_path is required")

    tmp_path: Optional[Path] = None
    try:
        if csv_file is not None:
            tmp_path = await _save_uploaded_file(csv_file)
            result = importer.import_csv(str(tmp_path))
        else:
            result = importer.import_csv(csv_path)  # type: ignore[arg-type]
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
    return ImportResult(**result)


@app.post("/cards", response_model=CardOutPT, status_code=201)
def create_card(payload: CardCreatePayload, db: Session = Depends(get_db)) -> CardOutPT:
    existing = (
        db.execute(
            select(Card).where(Card.set_id == payload.set_id, Card.number == payload.numero)
        )
        .scalars()
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Card já cadastrado para este conjunto e número")

    card = Card(name=payload.nome, set_id=payload.set_id, number=payload.numero)
    data = payload.model_dump()
    possui = data.pop("possui", False)
    _apply_card_payload(card, data)

    db.add(card)
    if possui:
        db.add(CollectionItem(card=card, quantity=1, for_trade=False))

    try:
        db.commit()
    except IntegrityError as exc:  # pragma: no cover - integridade do banco
        db.rollback()
        raise HTTPException(status_code=409, detail="Card já cadastrado") from exc

    card = _fetch_card(db, card.id) or card
    return _card_to_pt_schema(card)


@app.patch("/cards/{card_id}", response_model=CardOutPT)
def update_card_endpoint(
    card_id: int, payload: CardUpdatePayload, db: Session = Depends(get_db)
) -> CardOutPT:
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card não encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    possui = update_data.pop("possui", None)
    if update_data:
        _apply_card_payload(card, update_data)

    if possui is not None:
        items = (
            db.execute(select(CollectionItem).where(CollectionItem.card_id == card.id))
            .scalars()
            .all()
        )
        if possui:
            if not items:
                db.add(CollectionItem(card_id=card.id, quantity=1, for_trade=False))
        else:
            for item in items:
                db.delete(item)

    db.add(card)
    try:
        db.commit()
    except IntegrityError as exc:  # pragma: no cover - integridade do banco
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao atualizar a carta") from exc

    card = _fetch_card(db, card.id) or card
    return _card_to_pt_schema(card)


@app.get("/cards", response_model=List[CardOutPT])
def list_cards(
    q: Optional[str] = None,
    set_id: Optional[str] = None,
    rarity: Optional[str] = None,
    type: Optional[str] = None,
    number: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[CardOutPT]:
    statement = select(Card).options(selectinload(Card.collection_items), selectinload(Card.price_quotes))

    if q:
        statement = statement.where(Card.name.ilike(f"%{q}%"))
    if set_id:
        statement = statement.where(Card.set_id == set_id)
    if rarity:
        statement = statement.where(Card.rarity == rarity)
    if type:
        statement = statement.where(Card.types.ilike(f"%{type}%"))
    if number:
        statement = statement.where(Card.number == number)

    statement = statement.order_by(Card.name.asc()).offset(offset)
    if limit:
        statement = statement.limit(limit)

    results = db.execute(statement).scalars().all()
    return [_card_to_pt_schema(card) for card in results]


@app.get("/cards/{card_id}", response_model=CardOutPT)
def get_card(card_id: int, db: Session = Depends(get_db)) -> CardOutPT:
    card = _fetch_card(db, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card_to_pt_schema(card)


@app.post("/collection", response_model=CollectionOut, status_code=201)
def create_collection_item(payload: CollectionCreate, db: Session = Depends(get_db)) -> CollectionOut:
    card = db.get(Card, payload.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    item = CollectionItem(
        card_id=payload.card_id,
        quantity=payload.quantity,
        condition=payload.condition,
        for_trade=payload.for_trade,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    db.refresh(card)
    return _collection_to_schema(item)


@app.get("/collection", response_model=List[CollectionOut])
def list_collection_items(
    only_trade: bool = False,
    db: Session = Depends(get_db),
) -> List[CollectionOut]:
    statement = select(CollectionItem).options(
        joinedload(CollectionItem.card).options(
            selectinload(Card.collection_items),
            selectinload(Card.price_quotes),
        )
    )
    if only_trade:
        statement = statement.where(CollectionItem.for_trade.is_(True))
    statement = statement.order_by(CollectionItem.updated_at.desc())

    items = db.execute(statement).scalars().all()
    return [_collection_to_schema(item) for item in items]


@app.patch("/collection/{item_id}/trade", response_model=CollectionOut)
def toggle_trade_flag(
    item_id: int,
    for_trade: bool = Form(...),
    db: Session = Depends(get_db),
) -> CollectionOut:
    item = db.get(CollectionItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Collection item not found")

    item.for_trade = for_trade
    db.add(item)
    db.commit()
    db.refresh(item)
    return _collection_to_schema(item)


__all__ = ["app"]
