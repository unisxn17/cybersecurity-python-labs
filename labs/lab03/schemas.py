"""Pydantic-моделі запитів і відповідей."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from labs.lab03.config import BULK_MAX_ITEMS, SQLITE_INT_MAX, VALUE_MIN

Status = Literal["new", "in_progress", "done"]

STRICT_INPUT = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryCreate(BaseModel):
    """Тіло запиту на створення категорії."""

    model_config = STRICT_INPUT

    name: str = Field(min_length=2, max_length=40, examples=["backup_service"])


class CategoryRead(BaseModel):
    """Категорія (сервіс), яку повертає API."""

    id: int = Field(gt=0)
    name: str


class RecordCreate(BaseModel):
    """Тіло запиту на створення вимірювання; id створює база."""

    model_config = STRICT_INPUT

    code: str = Field(min_length=3, max_length=40, examples=["V08-TEST"])
    title: str = Field(min_length=3, max_length=120, examples=["Навчальне вимірювання"])
    category_id: int = Field(gt=0, le=SQLITE_INT_MAX, strict=True, examples=[1])
    value: float = Field(
        ge=VALUE_MIN,
        allow_inf_nan=False,
        strict=True,
        description="Час відновлення у хвилинах (скінченне число, не менше 0)",
        examples=[42.5],
    )
    status: Status = Field(examples=["new"])


class RecordReplace(RecordCreate):
    """Тіло PUT-запиту: усі змінювані поля обов’язкові."""


class RecordRead(RecordCreate):
    """Вимірювання разом з id та назвою категорії."""

    id: int
    category_name: str


class StudentRead(BaseModel):
    """Дані студента з shared/student.py."""

    student_name: str
    group_name: str
    variant_number: int


class ErrorMessage(BaseModel):
    """Опис очікуваної помилки."""

    detail: str


RecordBatch = Annotated[
    list[RecordCreate], Field(min_length=1, max_length=BULK_MAX_ITEMS)
]
