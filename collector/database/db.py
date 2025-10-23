"""SQLAlchemy configuration and database helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import Boolean, Integer, MetaData, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

_DB_PATH = Path(__file__).resolve().parent.parent / "collector.db"
metadata = MetaData()


def _sqlite_url() -> str:
    return f"sqlite:///{_DB_PATH}"


engine = create_engine(_sqlite_url(), echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = metadata


class Card(Base):
    """ORM model for Pokémon cards."""

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_type: Mapped[str] = mapped_column(String(100), nullable=False)
    rarity: Mapped[str | None] = mapped_column(String(100))
    set_name: Mapped[str | None] = mapped_column(String(255))
    number: Mapped[str | None] = mapped_column(String(50))
    stage: Mapped[str | None] = mapped_column(String(100))
    attacks: Mapped[str | None] = mapped_column(Text)
    weaknesses: Mapped[str | None] = mapped_column(Text)
    resistances: Mapped[str | None] = mapped_column(Text)
    retreat_cost: Mapped[str | None] = mapped_column(Text)
    artist: Mapped[str | None] = mapped_column(String(255))
    image_path: Mapped[str | None] = mapped_column(String(500))
    for_trade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


def init_db() -> None:
    """Create database tables if they do not exist."""

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
