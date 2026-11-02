"""Маршрути /records."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query, Response, status

from labs.lab03 import repository
from labs.lab03.config import BULK_MAX_ITEMS, SQLITE_INT_MAX, VALUE_MIN
from labs.lab03.schemas import (
    ErrorMessage,
    RecordBatch,
    RecordCreate,
    RecordRead,
    RecordReplace,
    Status,
)

router = APIRouter(prefix="/records", tags=["records"])

RecordId = Annotated[
    int, Path(gt=0, le=SQLITE_INT_MAX, description="Ідентифікатор запису")
]

NOT_FOUND = {
    404: {"model": ErrorMessage, "description": "Запис або категорію не знайдено"}
}
CONFLICT = {409: {"model": ErrorMessage, "description": "Дублікат code"}}


def _to_http(error: Exception) -> HTTPException:
    """Перетворити помилку шару даних на HTTP-помилку."""
    if isinstance(error, repository.NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    return HTTPException(status.HTTP_409_CONFLICT, str(error))


@router.get(
    "", summary="Список вимірювань із фільтрами", response_model=list[RecordRead]
)
def list_records(
    category_id: Annotated[
        int | None,
        Query(gt=0, le=SQLITE_INT_MAX, description="Лише записи цієї категорії"),
    ] = None,
    status_: Annotated[
        Status | None, Query(alias="status", description="Лише записи з цим статусом")
    ] = None,
    min_value: Annotated[
        float | None,
        Query(
            ge=VALUE_MIN, allow_inf_nan=False, description="value >= min_value, хвилини"
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=120, description="Буквальний підрядок у title"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Максимум записів")] = 20,
    offset: Annotated[
        int, Query(ge=0, le=SQLITE_INT_MAX, description="Скільки записів пропустити")
    ] = 0,
) -> list[dict]:
    """Повернути записи за зростанням id; фільтри поєднуються через AND."""
    return repository.list_records(category_id, status_, min_value, q, limit, offset)


@router.get(
    "/{record_id}",
    summary="Одне вимірювання",
    response_model=RecordRead,
    responses=NOT_FOUND,
)
def get_record(record_id: RecordId) -> dict:
    """Повернути запис за id разом із назвою категорії."""
    try:
        return repository.get_record(record_id)
    except repository.NotFoundError as error:
        raise _to_http(error) from error


@router.post(
    "",
    summary="Створити вимірювання",
    status_code=status.HTTP_201_CREATED,
    response_model=RecordRead,
    responses={**NOT_FOUND, **CONFLICT},
)
def create_record(record: RecordCreate) -> dict:
    """Створити запис; категорія має існувати, code — бути унікальним."""
    try:
        return repository.create_record(record.model_dump())
    except (repository.NotFoundError, repository.ConflictError) as error:
        raise _to_http(error) from error


@router.post(
    "/bulk",
    summary="Пакетне створення (атомарно)",
    status_code=status.HTTP_201_CREATED,
    response_model=list[RecordRead],
    responses={**NOT_FOUND, **CONFLICT},
)
def create_records_bulk(
    records: Annotated[
        RecordBatch,
        Body(description=f"JSON-масив від 1 до {BULK_MAX_ITEMS} об’єктів RecordCreate"),
    ],
) -> list[dict]:
    """Додати всі записи пакета в одній транзакції або не додати жодного."""
    try:
        return repository.create_records_bulk([r.model_dump() for r in records])
    except (repository.NotFoundError, repository.ConflictError) as error:
        raise _to_http(error) from error


@router.put(
    "/{record_id}",
    summary="Замінити вимірювання",
    response_model=RecordRead,
    responses={**NOT_FOUND, **CONFLICT},
)
def replace_record(record_id: RecordId, record: RecordReplace) -> dict:
    """Повністю замінити всі змінювані поля запису; id не змінюється."""
    try:
        return repository.replace_record(record_id, record.model_dump())
    except (repository.NotFoundError, repository.ConflictError) as error:
        raise _to_http(error) from error


@router.delete(
    "/{record_id}",
    summary="Видалити вимірювання",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND,
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис за id."""
    try:
        repository.delete_record(record_id)
    except repository.NotFoundError as error:
        raise _to_http(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
