from sqlalchemy import Column, Integer, String, Text

from .database import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    hp = Column(String, nullable=True)
    tipo = Column(String, nullable=True)
    raridade = Column(String, nullable=True)
    set = Column(String, nullable=True)
    set_id = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    artista = Column(String, nullable=True)
    habilidade_nome = Column(String, nullable=True)
    habilidade_desc = Column(Text, nullable=True)
    ataques = Column(Text, nullable=True)
    fraquezas = Column(String, nullable=True)
    resistencias = Column(String, nullable=True)
    recuo = Column(String, nullable=True)
    imagem = Column(String, nullable=True)
