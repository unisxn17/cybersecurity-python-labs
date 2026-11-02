"""Початкове заповнення бази з data/seed.json.

Запуск із кореня репозиторію: python -m labs.lab03.seed
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from labs.lab03 import repository
from labs.lab03.database import BASE_DIR, initialize_database
from labs.lab03.schemas import RecordCreate

SEED_PATH = BASE_DIR / "data" / "seed.json"

logger = logging.getLogger(__name__)


class SeedCategory(BaseModel):
    """Категорія з JSON; id задається явно."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=40)


class SeedData(BaseModel):
    """Структура seed.json: два масиви categories і records."""

    model_config = ConfigDict(extra="forbid")

    categories: list[SeedCategory]
    records: list[RecordCreate]


def load_seed(path: Path = SEED_PATH) -> SeedData:
    """Прочитати JSON і перевірити його вміст; ValueError, якщо дані некоректні."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Не вдалося прочитати {path.name}: {error}") from error
    try:
        return SeedData.model_validate(raw)
    except ValidationError as error:
        raise ValueError(f"Некоректні дані у {path.name}:\n{error}") from error


def seed() -> int:
    """Створити таблиці та заповнити порожню базу. Повертає код виходу."""
    try:
        data = load_seed()
    except ValueError as error:
        print(f"Помилка: {error}")
        return 1

    try:
        initialize_database()
        if not repository.is_database_empty():
            print("База вже містить дані — заповнення пропущено, зміни не внесено.")
            return 0
        repository.seed_database(
            [category.model_dump() for category in data.categories],
            [record.model_dump() for record in data.records],
        )
    except sqlite3.IntegrityError as error:
        logger.error("Порушення обмежень під час заповнення: %s", error)
        print("Помилка: дані порушують обмеження бази; жоден запис не збережено.")
        return 1
    except sqlite3.Error as error:
        logger.error("Помилка SQLite під час заповнення: %s", error)
        print("Помилка: не вдалося заповнити базу; зміни скасовано.")
        return 1

    print(
        f"Базу заповнено: {len(data.categories)} категорії, "
        f"{len(data.records)} записів."
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(seed())
