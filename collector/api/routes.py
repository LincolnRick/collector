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
    card: Optional[CardOut] = None


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
        card=_card_to_schema(item.card) if item.card else None,
    )


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "ts": datetime.utcnow().isoformat()}


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


@app.get("/cards", response_model=List[CardOut])
def list_cards(
    q: Optional[str] = None,
    set_id: Optional[str] = None,
    rarity: Optional[str] = None,
    type: Optional[str] = None,
    number: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[CardOut]:
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
    return [_card_to_schema(card) for card in results]


@app.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)) -> CardOut:
    card = (
        db.execute(
            select(Card)
            .options(selectinload(Card.collection_items), selectinload(Card.price_quotes))
            .where(Card.id == card_id)
        )
        .scalars()
        .first()
    )
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card_to_schema(card)


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
