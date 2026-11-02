# Лабораторна робота №3 — Web API на FastAPI та SQLite

**Варіант 8:** облік часу відновлення сервісів.

| Поле          | Значення                                                    |
|---------------|-------------------------------------------------------------|
| Категорії     | `database`, `web_service`, `file_storage` (сервіс)          |
| `value`       | час відновлення, `float`, не менше 0, одиниця — `minutes`   |
| `status`      | стан перевірки вимірювання: `new`, `in_progress`, `done`    |
| Поріг         | `60.0` хвилин                                               |
| Назва запису  | `Вимірювання відновлення NN`, `code` — `V08-NN`             |

## Встановлення

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Усі команди виконуються з кореня репозиторію.

## Структура

```
labs/lab03/
├── main.py           # FastAPI-застосунок, /ping, /student, lifespan
├── database.py       # з’єднання (PRAGMA foreign_keys = ON) і виконання schema.sql
├── schema.sql        # готова схема для варіантів 7–9
├── repository.py     # параметризовані SQL-запити, транзакції
├── schemas.py        # Pydantic-моделі запитів і відповідей
├── config.py         # одиниця вимірювання, поріг, обмеження варіанта
├── seed.py           # початкове заповнення з data/seed.json
├── routers/
│   ├── categories.py # /categories
│   └── records.py    # /records, /records/bulk
└── data/
    ├── seed.json     # навчальні дані: 3 категорії, 8 записів
    └── lab3.sqlite3  # створюється програмою, у Git не додається
```

## Запуск

```bash
python -m labs.lab03.database   # лише створити таблиці (необов’язково)
python -m labs.lab03.seed       # створити таблиці й заповнити порожню базу
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

Повторний запуск `seed` не змінює непорожню базу. Документація API:
<http://127.0.0.1:8000/docs> (Swagger UI) та <http://127.0.0.1:8000/openapi.json>.

## Маршрути

| Метод і маршрут                    | Успіх                | Помилки       |
|------------------------------------|----------------------|---------------|
| `GET /ping`                        | 200 `{"status":"ok"}`|               |
| `GET /student`                     | 200                  |               |
| `GET /categories`                  | 200                  |               |
| `POST /categories`                 | 201                  | 409, 422      |
| `DELETE /categories/{category_id}` | 204                  | 404, 409, 422 |
| `GET /records`                     | 200                  | 422           |
| `GET /records/{record_id}`         | 200                  | 404, 422      |
| `POST /records`                    | 201                  | 404, 409, 422 |
| `PUT /records/{record_id}`         | 200                  | 404, 409, 422 |
| `DELETE /records/{record_id}`      | 204                  | 404, 422      |
| `POST /records/bulk`               | 201                  | 404, 409, 422 |

Параметри `GET /records`: `category_id` (> 0), `status`, `min_value` (≥ 0),
`q` (буквальний підрядок у `title`, 1–120 символів), `limit` (1–100, типово 20),
`offset` (≥ 0, типово 0). Фільтри поєднуються через `AND`, сортування — за `id`.

`POST /records/bulk` приймає JSON-масив від 1 до 100 записів і зберігає їх в одній
транзакції: якщо хоч один елемент має дублікат `code` або неіснуючу категорію,
не зберігається жоден.

## Приклади запитів

```bash
curl -i "http://127.0.0.1:8000/ping"
curl -i "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5&offset=0"
curl -i "http://127.0.0.1:8000/records?min_value=60"

curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V08-TEST","title":"Навчальне вимірювання","category_id":1,"value":42.5,"status":"new"}'

curl -i -X PUT "http://127.0.0.1:8000/records/9" \
  -H "Content-Type: application/json" \
  -d '{"code":"V08-TEST","title":"Оновлене вимірювання","category_id":3,"value":61.0,"status":"done"}'

curl -i -X DELETE "http://127.0.0.1:8000/records/9"

# Скасування пакета: V08-01 уже є в базі -> 409, V08-ROLLBACK не збережено
curl -i -X POST "http://127.0.0.1:8000/records/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"code":"V08-ROLLBACK","title":"Перший елемент","category_id":1,"value":4.0,"status":"new"},{"code":"V08-01","title":"Дублікат коду","category_id":2,"value":5.0,"status":"new"}]'

# Спроба SQL-ін’єкції обробляється як звичайний текст -> 200, []
curl -i -G "http://127.0.0.1:8000/records" --data-urlencode "q=' OR 1=1 --"
```

## Перевірка стилю

```bash
ruff check labs/lab03
ruff format --check labs/lab03
```
