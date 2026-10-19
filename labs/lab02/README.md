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

| Мітка | Умова |
|---|---|
| `BLACKMATCH` | домен або його батьківський домен є в чорному списку |
| `LONG-DOMAIN(n)` | довжина домену ≥ `--min-domain-len` |
| `LONG-SUBDOMAIN` | будь-яка мітка домену має ≥ 40 символів (regex) |
| `DGA-DETECT` | мітка з ≥ 12 літер і цифр (обидва типи) з ентропією Шеннона ≥ 3.0 |
| `SUSPICIOUS-TLD(.x)` | TLD зі списку `.zip .top .xyz .click .loan .work .gq .tk .ml .cf` |
| `LONG-TXT` | TXT-запит до довгого домену (можливий DNS-тунель) |

Статистика типів запитів рахується через `collections.Counter`, вихідний CSV має
колонки `Timestamp,ClientIP,Domain,QueryType,Length,Reasons`.

### Поведінка при помилках

- Вхідний файл не знайдено або його не вдалося прочитати: `[ERROR]` у лог, код виходу `1`.
- У CSV немає потрібних колонок: `[ERROR]`, код виходу `1`.
- Рядок із некоректною датою чи доменом: `[WARNING] Line N skipped`, обробка триває.
- Неправильне значення `--min-domain-len` (не число або ≤ 0): помилка argparse, код виходу `2`.

## Перевірка коду

```bash
ruff check .
ruff format --check .
```
