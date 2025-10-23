"""FastAPI routes for the collector application."""

from __future__ import annotations

import json
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from collector.database.db import Card, SessionLocal, init_db
from collector.models import PokemonCard, Attack, Effect

init_db()
app = FastAPI(title="Collector API", version="0.1.0")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["status"])
def healthcheck() -> dict[str, str]:
    """Simple healthcheck endpoint."""

    return {"status": "ok"}


@app.get("/cards", response_model=List[PokemonCard])
def list_cards(db: Session = Depends(get_db)) -> List[PokemonCard]:
    """Return cards stored in the database."""

    records = db.query(Card).all()
    return [
        PokemonCard(
            name=record.name,
            hp=record.hp,
            type=record.card_type,
            rarity=record.rarity,
            set_name=record.set_name,
            number=record.number,
            stage=record.stage,
            attacks=[Attack(**attack) for attack in json.loads(record.attacks)] if record.attacks else [],
            weaknesses=[Effect(**effect) for effect in json.loads(record.weaknesses)] if record.weaknesses else [],
            resistances=[Effect(**effect) for effect in json.loads(record.resistances)] if record.resistances else [],
            retreat_cost=json.loads(record.retreat_cost) if record.retreat_cost else [],
            artist=record.artist,
            image=record.image_path,
            for_trade=record.for_trade,
        )
        for record in records
    ]


@app.post("/cards", response_model=PokemonCard, status_code=status.HTTP_201_CREATED)
def create_card(card: PokemonCard, db: Session = Depends(get_db)) -> PokemonCard:
    """Create a new card entry."""

    db_card = Card(
        name=card.name,
        hp=card.hp,
        card_type=card.card_type,
        rarity=card.rarity,
        set_name=card.set_name,
        number=card.number,
        stage=card.stage,
        attacks=json.dumps([attack.dict() for attack in card.attacks]) if card.attacks else None,
        weaknesses=json.dumps([effect.dict() for effect in card.weaknesses]) if card.weaknesses else None,
        resistances=json.dumps([effect.dict() for effect in card.resistances]) if card.resistances else None,
        retreat_cost=json.dumps(card.retreat_cost) if card.retreat_cost else None,
        artist=card.artist,
        image_path=card.image,
        for_trade=card.for_trade,
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)

    return card


@app.get("/cards/{card_id}", response_model=PokemonCard)
def get_card(card_id: int, db: Session = Depends(get_db)) -> PokemonCard:
    """Retrieve a single card by identifier."""

    record = db.query(Card).get(card_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    return PokemonCard(
        name=record.name,
        hp=record.hp,
        type=record.card_type,
        rarity=record.rarity,
        set_name=record.set_name,
        number=record.number,
        stage=record.stage,
        attacks=[Attack(**attack) for attack in json.loads(record.attacks)] if record.attacks else [],
        weaknesses=[Effect(**effect) for effect in json.loads(record.weaknesses)] if record.weaknesses else [],
        resistances=[Effect(**effect) for effect in json.loads(record.resistances)] if record.resistances else [],
        retreat_cost=json.loads(record.retreat_cost) if record.retreat_cost else [],
        artist=record.artist,
        image=record.image_path,
        for_trade=record.for_trade,
    )
