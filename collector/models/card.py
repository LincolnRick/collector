"""Pydantic models describing Pokémon cards."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Attack(BaseModel):
    """Representation of a Pokémon attack."""

    name: str = Field(..., description="Name of the attack")
    cost: List[str] = Field(default_factory=list, description="Energy cost required to perform the attack")
    damage: Optional[str] = Field(None, description="Damage dealt by the attack")
    text: Optional[str] = Field(None, description="Additional rules or effects of the attack")


class Effect(BaseModel):
    """Representation of a weakness or resistance."""

    type: str = Field(..., description="Elemental type affected")
    value: str = Field(..., description="Modifier applied to damage")


class PokemonCard(BaseModel):
    """Data model for a Pokémon trading card."""

    name: str = Field(..., description="Card name")
    hp: Optional[int] = Field(None, description="Hit Points of the Pokémon")
    card_type: str = Field(..., alias="type", description="Pokémon type")
    rarity: Optional[str] = Field(None, description="Rarity classification")
    set_name: Optional[str] = Field(None, description="Expansion set name")
    number: Optional[str] = Field(None, description="Card number within the set")
    stage: Optional[str] = Field(None, description="Evolution stage")
    attacks: List[Attack] = Field(default_factory=list, description="List of attacks available")
    weaknesses: List[Effect] = Field(default_factory=list, description="Card weaknesses")
    resistances: List[Effect] = Field(default_factory=list, description="Card resistances")
    retreat_cost: List[str] = Field(default_factory=list, description="Retreat cost energies")
    artist: Optional[str] = Field(None, description="Illustrator of the card")
    image: Optional[str] = Field(None, description="Path or URL to the card image")
    for_trade: bool = Field(False, description="Indicates if the card is available for trading")

    class Config:
        allow_population_by_field_name = True
