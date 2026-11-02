"""FastAPI-застосунок ЛР №3 (варіант 8).

Запуск із кореня репозиторію:
    uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from labs.lab03.config import APP_DESCRIPTION, APP_TITLE
from labs.lab03.database import initialize_database
from labs.lab03.routers import categories, records
from labs.lab03.schemas import StudentRead
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску, не змінюючи наявних даних."""
    initialize_database()
    yield


app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, lifespan=lifespan)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    """Повернути 422 без поля input.

    Вхідне значення не повертається клієнту: нескінченність (1e999) неможливо
    серіалізувати в JSON, і стандартна відповідь FastAPI падала б із 500.
    """
    details = [
        {"type": item["type"], "loc": list(item["loc"]), "msg": item["msg"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(sqlite3.Error)
def handle_database_error(_: Request, error: sqlite3.Error) -> JSONResponse:
    """Записати технічну помилку в журнал і повернути клієнту загальне повідомлення."""
    logger.exception("Помилка бази даних: %s", error)
    return JSONResponse(
        status_code=500, content={"detail": "Внутрішня помилка сервера"}
    )


@app.get("/ping", summary="Перевірка доступності API", tags=["service"])
def ping() -> dict[str, str]:
    """Повернути {"status": "ok"}."""
    return {"status": "ok"}


@app.get(
    "/student", summary="Дані студента", response_model=StudentRead, tags=["service"]
)
def student() -> StudentRead:
    """Повернути ПІБ, групу та номер варіанта."""
    return StudentRead(
        student_name=STUDENT_NAME,
        group_name=GROUP_NAME,
        variant_number=int(VARIANT_NUMBER),
    )
