"""Маршрути /categories."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status

from labs.lab03 import repository
from labs.lab03.config import SQLITE_INT_MAX
from labs.lab03.schemas import CategoryCreate, CategoryRead, ErrorMessage

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryId = Annotated[
    int, Path(gt=0, le=SQLITE_INT_MAX, description="Ідентифікатор категорії")
]


@router.get("", summary="Список категорій", response_model=list[CategoryRead])
def list_categories() -> list[dict]:
    """Повернути всі категорії (сервіси) за зростанням id."""
    return repository.list_categories()


@router.post(
    "",
    summary="Створити категорію",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryRead,
    responses={409: {"model": ErrorMessage, "description": "Назва вже існує"}},
)
def create_category(category: CategoryCreate) -> dict:
    """Створити нову категорію; id призначає база."""
    try:
        return repository.create_category(category.name)
    except repository.ConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.delete(
    "/{category_id}",
    summary="Видалити порожню категорію",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorMessage, "description": "Категорію не знайдено"},
        409: {"model": ErrorMessage, "description": "Категорія містить записи"},
    },
)
def delete_category(category_id: CategoryId) -> Response:
    """Видалити категорію, якщо до неї не прив’язано жодного запису."""
    try:
        repository.delete_category(category_id)
    except repository.NotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except repository.ConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
