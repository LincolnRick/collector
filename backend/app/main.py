from fastapi import FastAPI

from .database import Base, engine
from .routes.cards import router as cards_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pokedex Collector API")

app.include_router(cards_router)
