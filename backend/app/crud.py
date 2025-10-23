from sqlalchemy.orm import Session

from . import models, schemas


def get_cards(db: Session):
    return db.query(models.Card).all()


def create_card(db: Session, card: schemas.CardCreate):
    db_card = models.Card(**card.dict())
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def update_card(db: Session, card_id: int, payload: schemas.CardUpdate):
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if db_card is None:
        return None

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_card, field, value)

    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card
