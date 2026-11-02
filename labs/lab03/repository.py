"""Параметризовані SQL-запити. Модуль не залежить від FastAPI."""

import sqlite3
from collections.abc import Iterable
from contextlib import closing
from typing import Any

from labs.lab03.database import get_connection

RECORD_SELECT = """
    SELECT r.id, r.code, r.title, r.category_id, r.value, r.status,
           c.name AS category_name
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""


class NotFoundError(Exception):
    """Запис або категорія не існує."""


class ConflictError(Exception):
    """Порушено унікальність або категорія містить записи."""


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    return {col[0]: value for col, value in zip(cursor.description, row)}


def _connect() -> sqlite3.Connection:
    connection = get_connection()
    connection.row_factory = _row_to_dict
    return connection


def _category_exists(connection: sqlite3.Connection, category_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return row is not None


def _fetch_record(connection: sqlite3.Connection, record_id: int) -> dict | None:
    return connection.execute(
        RECORD_SELECT + " WHERE r.id = ?", (record_id,)
    ).fetchone()


def _record_params(record: dict[str, Any]) -> tuple:
    return (
        record["code"],
        record["title"],
        record["category_id"],
        record["value"],
        record["status"],
    )


def _code_conflict(error: sqlite3.IntegrityError, code: str = "") -> ConflictError:
    if "UNIQUE" in str(error):
        suffix = f" '{code}'" if code else ""
        return ConflictError(f"Запис із таким code{suffix} уже існує")
    return ConflictError("Дані порушують обмеження бази")


# --- Категорії -------------------------------------------------------------


def list_categories() -> list[dict]:
    """Повернути всі категорії за зростанням id."""
    with closing(_connect()) as connection:
        return connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()


def create_category(name: str) -> dict:
    """Створити категорію; ConflictError, якщо назва вже зайнята."""
    with closing(_connect()) as connection:
        try:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)", (name,)
                )
        except sqlite3.IntegrityError as error:
            raise ConflictError(f"Категорія '{name}' уже існує") from error
        return {"id": cursor.lastrowid, "name": name}


def delete_category(category_id: int) -> None:
    """Видалити порожню категорію."""
    with closing(_connect()) as connection, connection:
        if not _category_exists(connection, category_id):
            raise NotFoundError("Категорію не знайдено")
        used = connection.execute(
            "SELECT 1 FROM records WHERE category_id = ? LIMIT 1",
            (category_id,),
        ).fetchone()
        if used:
            raise ConflictError("Категорія містить записи")
        try:
            connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        except sqlite3.IntegrityError as error:
            raise ConflictError("Категорія містить записи") from error


# --- Записи ----------------------------------------------------------------


def list_records(
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Повернути записи з фільтрами (через AND) і поділом на сторінки."""
    # SQL-фрагменти лише з фіксованих рядків; значення — окремим списком.
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)

    sql = RECORD_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with closing(_connect()) as connection:
        return connection.execute(sql, params).fetchall()


def get_record(record_id: int) -> dict:
    """Повернути запис за id."""
    with closing(_connect()) as connection:
        record = _fetch_record(connection, record_id)
    if record is None:
        raise NotFoundError("Запис не знайдено")
    return record


def create_record(record: dict[str, Any]) -> dict:
    """Додати запис і повернути його разом із category_name."""
    with closing(_connect()) as connection:
        try:
            with connection:
                if not _category_exists(connection, record["category_id"]):
                    raise NotFoundError("Категорію не знайдено")
                cursor = connection.execute(
                    "INSERT INTO records (code, title, category_id, value, status)"
                    " VALUES (?, ?, ?, ?, ?)",
                    _record_params(record),
                )
        except sqlite3.IntegrityError as error:
            raise _code_conflict(error, record["code"]) from error
        return _fetch_record(connection, cursor.lastrowid)


def replace_record(record_id: int, record: dict[str, Any]) -> dict:
    """Повністю замінити змінювані поля; id не змінюється."""
    with closing(_connect()) as connection:
        try:
            with connection:
                if _fetch_record(connection, record_id) is None:
                    raise NotFoundError("Запис не знайдено")
                if not _category_exists(connection, record["category_id"]):
                    raise NotFoundError("Категорію не знайдено")
                connection.execute(
                    "UPDATE records"
                    " SET code = ?, title = ?, category_id = ?, value = ?, status = ?"
                    " WHERE id = ?",
                    (*_record_params(record), record_id),
                )
        except sqlite3.IntegrityError as error:
            raise _code_conflict(error, record["code"]) from error
        return _fetch_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити запис за id."""
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM records WHERE id = ?", (record_id,)
            )
        if cursor.rowcount == 0:
            raise NotFoundError("Запис не знайдено")


def create_records_bulk(records: list[dict[str, Any]]) -> list[dict]:
    """Додати пакет записів в одній транзакції: усі або жодного."""
    codes = [record["code"] for record in records]
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    if duplicates:
        raise ConflictError(f"Повторний code у пакеті: {', '.join(duplicates)}")

    with closing(_connect()) as connection:
        try:
            with connection:
                # Явний BEGIN: перевірка категорій і вставка в одній транзакції.
                connection.execute("BEGIN")
                for category_id in {record["category_id"] for record in records}:
                    if not _category_exists(connection, category_id):
                        raise NotFoundError(f"Категорію {category_id} не знайдено")
                new_ids = []
                for record in records:
                    cursor = connection.execute(
                        "INSERT INTO records"
                        " (code, title, category_id, value, status)"
                        " VALUES (?, ?, ?, ?, ?)",
                        _record_params(record),
                    )
                    new_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise _code_conflict(error) from error
        return [_fetch_record(connection, record_id) for record_id in new_ids]


# --- Початкове заповнення --------------------------------------------------


def is_database_empty() -> bool:
    """Перевірити, що в базі ще немає категорій і записів."""
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT (SELECT COUNT(*) FROM categories)"
            " + (SELECT COUNT(*) FROM records) AS total"
        ).fetchone()
    return row["total"] == 0


def seed_database(
    categories: Iterable[dict[str, Any]], records: Iterable[dict[str, Any]]
) -> None:
    """Вставити категорії з заданими id і записи в одній транзакції."""
    with closing(_connect()) as connection, connection:
        connection.executemany(
            "INSERT INTO categories (id, name) VALUES (?, ?)",
            [(category["id"], category["name"]) for category in categories],
        )
        connection.executemany(
            "INSERT INTO records (code, title, category_id, value, status)"
            " VALUES (?, ?, ?, ?, ?)",
            [_record_params(record) for record in records],
        )
