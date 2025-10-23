"""SQLAlchemy models used by the Collector backend."""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TimestampMixin:
    """Shared timestamp columns for created/updated tracking."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Card(Base, TimestampMixin):
    """Represents a Pokémon card imported from CSV datasets."""

    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("set_id", "number", name="uq_cards_set_number"),
        Index("ix_cards_name", "name"),
        Index("ix_cards_set_id", "set_id"),
        Index("ix_cards_rarity", "rarity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hp: Mapped[str | None] = mapped_column(String(50), nullable=True)
    types: Mapped[str | None] = mapped_column(Text, nullable=True)
    rarity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    set_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    set_id: Mapped[str] = mapped_column(String(100), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ability_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ability_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attacks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="JSON payload grouping CSV columns prefixed with 'attacks_'",
    )
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    resistances: Mapped[str | None] = mapped_column(Text, nullable=True)
    retreat_cost: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    collection_items: Mapped[List["CollectionItem"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )
    price_quotes: Mapped[List["PriceQuote"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Card(id={self.id!r}, name={self.name!r}, set_id={self.set_id!r}, number={self.number!r})"


class CollectionItem(Base, TimestampMixin):
    """Represents an item owned in the local collection."""

    __tablename__ = "collection_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="chk_collection_quantity_positive"),
        Index("ix_collection_card_id", "card_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    for_trade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    card: Mapped[Card] = relationship(back_populates="collection_items")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"CollectionItem(id={self.id!r}, card_id={self.card_id!r}, quantity={self.quantity!r})"


class PriceQuote(Base):
    """Price information fetched from external marketplaces."""

    __tablename__ = "price_quotes"
    __table_args__ = (
        CheckConstraint("avg_price >= 0", name="chk_price_avg_positive"),
        CheckConstraint("min_price >= 0", name="chk_price_min_positive"),
        CheckConstraint("max_price >= 0", name="chk_price_max_positive"),
        Index("ix_price_quotes_card_id", "card_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    avg_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    min_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    card: Mapped[Card] = relationship(back_populates="price_quotes")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"PriceQuote(id={self.id!r}, card_id={self.card_id!r}, source={self.source!r})"
