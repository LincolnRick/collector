"""Seed script to populate the database from a CSV file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

from collector.database.db import Card, SessionLocal, init_db
from collector.utils import load_image, save_image_copy

EXPECTED_HEADERS = {
    "name",
    "hp",
    "type",
    "rarity",
    "set",
    "number",
    "stage",
    "attacks",
    "weaknesses",
    "resistances",
    "retreat",
    "artist",
    "image",
    "for_trade",
}


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "sim"}


def load_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        missing_headers = EXPECTED_HEADERS - set(reader.fieldnames or [])
        if missing_headers:
            raise ValueError(f"Missing columns in CSV: {', '.join(sorted(missing_headers))}")
        yield from reader


def seed_database(csv_path: Path, image_dir: Path, output_dir: Path) -> None:
    init_db()
    output_dir.mkdir(parents=True, exist_ok=True)
    session = SessionLocal()
    try:
        for row in load_rows(csv_path):
            image_source = image_dir / row["image"] if row.get("image") else None
            stored_image = None
            if image_source and image_source.exists():
                image = load_image(image_source)
                if image:
                    stored_path = output_dir / row["image"]
                    save_image_copy(image, stored_path)
                    image.close()
                    stored_image = stored_path.as_posix()
            card = Card(
                name=row["name"],
                hp=int(row["hp"]) if row.get("hp") else None,
                card_type=row["type"],
                rarity=row.get("rarity"),
                set_name=row.get("set"),
                number=row.get("number"),
                stage=row.get("stage"),
                attacks=row.get("attacks"),
                weaknesses=row.get("weaknesses"),
                resistances=row.get("resistances"),
                retreat_cost=row.get("retreat"),
                artist=row.get("artist"),
                image_path=stored_image,
                for_trade=parse_bool(row.get("for_trade", "false")),
            )
            session.add(card)
        session.commit()
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the collector database from CSV data.")
    parser.add_argument("csv", type=Path, help="Path to the CSV file containing card data.")
    parser.add_argument(
        "image_dir",
        type=Path,
        help="Directory containing the original card images referenced by the CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("collector_images"),
        help="Destination directory where images should be copied.",
    )
    args = parser.parse_args()

    seed_database(args.csv, args.image_dir, args.output)


if __name__ == "__main__":
    main()
