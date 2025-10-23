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
