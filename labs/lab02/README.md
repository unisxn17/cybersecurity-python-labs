# Лабораторна робота №2 — консольні утиліти для задач кібербезпеки

**Варіант 8:** Фільтр та аналізатор журналів DNS-запитів.

## Встановлення

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Усі команди виконуються з кореня репозиторію.

## Структура

```
labs/lab02/
├── __init__.py
├── main.py        # команди demo та analyze
├── task1.py       # User, Admin, Session, AuditLog, UserAccount
├── task2.py       # аналізатор DNS-запитів
├── README.md
└── data/
    └── data_v08/            # каталог варіанта з lab2_data.zip
        ├── dns_queries.csv  # вхід: журнал DNS (Timestamp,ClientIP,Domain,QueryType)
        └── blacklist.txt    # вхід: чорний список, один домен на рядок
```

## Завдання 1 — демонстрація ООП

```bash
python -m labs.lab02.main demo
```

Показує успішний і невдалий вхід, зміну email із валідацією, права адміністратора,
завершення сеансу за таймаутом, вихід із системи та записи `AuditLog`.

## Завдання 2 — аналізатор DNS

```bash
python -m labs.lab02.main analyze
python -m labs.lab02.main analyze \
    --dns-log labs/lab02/data/data_v08/dns_queries.csv \
    --blacklist labs/lab02/data/data_v08/blacklist.txt \
    --out-csv labs/lab02/data/data_v08/dns_alerts.csv \
    --min-domain-len 50
```

Утиліту також можна запустити напряму: `python -m labs.lab02.task2 --help`.

| Аргумент | Опис | Типово |
|---|---|---|
| `--dns-log` | CSV-журнал DNS-запитів | `labs/lab02/data/data_v08/dns_queries.csv` |
| `--blacklist` | файл чорного списку (`#` — коментар) | `labs/lab02/data/data_v08/blacklist.txt` |
| `--out-csv` | куди записати аномальні запити | `labs/lab02/data/data_v08/dns_alerts.csv` |
| `--min-domain-len` | довжина домену, з якої він вважається аномальним (ціле > 0) | `50` |

### Правила виявлення

| Причина | Умова |
|---|---|
| `blacklisted` | домен є в чорному списку |
| `long subdomain` | у домені є частина з ≥ 30 символів (regex) — типово для DGA і DNS-тунелів |
| `suspicious TLD .x` | домен у зоні `.zip .top .xyz .click .tk .gq` (regex) |
| `length N` | довжина домену ≥ `--min-domain-len` |

Статистика типів запитів рахується через `collections.Counter`. Вихідний CSV має
колонки `Timestamp,ClientIP,Domain,QueryType,Reasons`.

### Поведінка при помилках

- Вхідний файл не знайдено або не вдалося прочитати: `[ERROR]` у лог, код виходу `1`.
- У CSV немає потрібних колонок: `[ERROR]`, код виходу `1`.
- Рядок із некоректною датою: `[WARNING] Line N skipped`, обробка триває.
- `--min-domain-len` не є цілим числом > 0: помилка argparse, код виходу `2`.

## Перевірка коду

```bash
ruff check .
ruff format --check .
```
