from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/", response_model=List[schemas.Card])
def read_cards(db: Session = Depends(get_db)):
    cards = crud.get_cards(db)
    return cards


@router.post("/", response_model=schemas.Card, status_code=status.HTTP_201_CREATED)
def create_card(card: schemas.CardCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_card(db, card)
    except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc
