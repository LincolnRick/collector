"""Utility script to populate the Collector database."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from collector.db import Base, SessionLocal, engine
from collector.models import Card, CollectionItem
from collector.services.importer import import_csv
from collector.services.images import guess_local_image

load_dotenv()


def _dump(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _ensure_dummy_data() -> None:
    session = SessionLocal()
    try:
        if session.query(Card).count() > 0:
            return

        pikachu = Card(
            name="Pikachu",
            hp="60",
            types=_dump(["Lightning"]),
            rarity="Common",
            set_name="Base Set",
            set_id="base",
            number="58",
            artist="Ken Sugimori",
            attacks=json.dumps(
                [
                    {
                        "name": "Thunder Jolt",
                        "cost": ["Lightning"],
                        "damage": "30",
                        "text": "Flip a coin. If tails, Pikachu does 10 damage to itself.",
                    }
                ],
                ensure_ascii=False,
            ),
            weaknesses=_dump(["Fighting"]),
            resistances=_dump([]),
            retreat_cost=_dump(["Colorless"]),
            image_path=guess_local_image("base", "58"),
            image_url="https://images.pokemontcg.io/base1/58_hires.png",
        )

        charmander = Card(
            name="Charmander",
            hp="50",
            types=_dump(["Fire"]),
            rarity="Common",
            set_name="Base Set",
            set_id="base",
            number="46",
            artist="Mitsuhiro Arita",
            attacks=json.dumps(
                [
                    {
                        "name": "Scratch",
                        "cost": ["Colorless"],
                        "damage": "10",
                        "text": None,
                    },
                    {
                        "name": "Ember",
                        "cost": ["Fire", "Colorless"],
                        "damage": "30",
                        "text": "Discard 1 Fire Energy card attached to Charmander in order to use this attack.",
                    },
                ],
                ensure_ascii=False,
            ),
            weaknesses=_dump(["Water"]),
            resistances=_dump([]),
            retreat_cost=_dump(["Colorless"]),
            image_path=guess_local_image("base", "46"),
            image_url="https://images.pokemontcg.io/base1/46_hires.png",
        )

        session.add_all([pikachu, charmander])
        session.flush()

        collection_item = CollectionItem(card_id=pikachu.id, quantity=1, for_trade=True)
        session.add(collection_item)
        session.commit()
    finally:
        session.close()


def seed_from_csv(csv_path: Path) -> None:
    result = import_csv(str(csv_path))
    print(
        f"Imported {result['created']} cards, {result['updated']} updated and {result['skipped']} skipped from {csv_path}"
    )


def resolve_csv_path(cli_path: Optional[Path]) -> Optional[Path]:
    if cli_path:
        return cli_path
    env_path = os.getenv("CSV_PATH")
    if env_path:
        return Path(env_path)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Collector database.")
    parser.add_argument("csv", nargs="?", type=Path, help="Optional path to the CSV dataset")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    csv_path = resolve_csv_path(args.csv)
    if csv_path and csv_path.exists():
        seed_from_csv(csv_path)
    else:
        if csv_path:
            print(f"CSV file {csv_path} not found. Falling back to dummy data.")
        _ensure_dummy_data()
        print("Dummy data ensured in the database.")


if __name__ == "__main__":
    main()
