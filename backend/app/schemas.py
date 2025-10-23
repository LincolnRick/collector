from typing import Optional

from pydantic import BaseModel


class CardBase(BaseModel):
    nome: str
    hp: Optional[str] = None
    tipo: Optional[str] = None
    raridade: Optional[str] = None
    set: Optional[str] = None
    set_id: Optional[str] = None
    numero: Optional[str] = None
    artista: Optional[str] = None
    habilidade_nome: Optional[str] = None
    habilidade_desc: Optional[str] = None
    ataques: Optional[str] = None
    fraquezas: Optional[str] = None
    resistencias: Optional[str] = None
    recuo: Optional[str] = None
    imagem: Optional[str] = None
    possui: Optional[bool] = False


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    nome: Optional[str] = None
    hp: Optional[str] = None
    tipo: Optional[str] = None
    raridade: Optional[str] = None
    set: Optional[str] = None
    set_id: Optional[str] = None
    numero: Optional[str] = None
    artista: Optional[str] = None
    habilidade_nome: Optional[str] = None
    habilidade_desc: Optional[str] = None
    ataques: Optional[str] = None
    fraquezas: Optional[str] = None
    resistencias: Optional[str] = None
    recuo: Optional[str] = None
    imagem: Optional[str] = None
    possui: Optional[bool] = None


class Card(CardBase):
    id: int

    class Config:
        orm_mode = True
