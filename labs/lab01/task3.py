import csv
import datetime
import hashlib
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER


class ValidationError(Exception):
    """Виникає, якщо пароль коротший за мінімальну довжину."""


MIN_PASSWORD_LENGTH = 11
PERSONAL_SALT = str(VARIANT_NUMBER).zfill(5)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
LOG_JSON = os.path.join(DATA_DIR, "log.json")

users_to_register = (
    ("alice", "Str0ngP@ssword1"),
    ("bob", "An0therSecur3!"),
    ("carol", "MyP@ssphrase99"),
    ("dave", "S3cur3P@ss2023"),
    ("erin", "C0mplex#Pass1"),
    ("frank", "Sh0rt"),
    ("grace", "Pr0tect3d@Data"),
    ("heidi", "Vault!K3eper9"),
    ("ivan", "Cyb3r@Def3nse"),
    ("judy", "L0ckdown#2023"),
)


def generate_hash(password: str, salt: str = "00000") -> str:
    if not password or not salt:
        raise ValueError("Пароль та сіль не можуть бути порожніми")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Пароль коротший за мінімальну довжину ({MIN_PASSWORD_LENGTH})"
        )
    return hashlib.sha256((password + salt).encode()).hexdigest()


def create_user(username, password):
    hash_value = generate_hash(password, PERSONAL_SALT)
    return username, hash_value


def create_users(users_list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USERS_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for username, password in users_list:
            try:
                username, hash_value = create_user(username, password)
                writer.writerow([username, hash_value])
            except ValidationError as error:
                print(f"Пропущено {username}: {error}")


def read_users_db():
    users_db = []
    with open(USERS_CSV, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            users_db.append(tuple(row))
    return users_db


def print_users_db(users_db):
    print(f"{'Логін':<15} {'Хеш':<70}")
    print("-" * 85)
    for username, hash_value in users_db:
        print(f"{username:<15} {hash_value:<70}")


def log_event(func):
    
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        entry = {
            "event": "login",
            "user": args[0] if args else kwargs.get("username", ""),
            "result": "success" if result else "failure",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # noqa: DTZ005
            "args": list(args),
            "kwargs": kwargs,
        }

        os.makedirs(DATA_DIR, exist_ok=True)
        logs = []
        if os.path.exists(LOG_JSON):
            with open(LOG_JSON, "r", encoding="utf-8") as file:
                try:
                    logs = json.load(file)
                except json.JSONDecodeError:
                    logs = []

        logs.append(entry)
        with open(LOG_JSON, "w", encoding="utf-8") as file:
            json.dump(logs, file, indent=2, ensure_ascii=False)

        return result

    return wrapper


@log_event
def login(username: str, password: str) -> bool:
    
    if not username or not password:
        raise ValueError("Логін та пароль не можуть бути порожніми")

    hash_value = generate_hash(password, PERSONAL_SALT)
    users_db = read_users_db()

    for db_username, db_hash in users_db:
        if db_username == username and db_hash == hash_value:
            return True
    return False


def main():
    print(f"{STUDENT_NAME}, {GROUP_NAME}, Варіант: {VARIANT_NUMBER}")

    try:
        create_users(users_to_register)
        users_db = read_users_db()
        print_users_db(users_db)

        test_username, test_password = users_to_register[0]
        result = login(test_username, test_password)
        print(f"\nВхід '{test_username}' з правильним паролем: {'успішно' if result else 'невдало'}")

        result_wrong = login(test_username, "wrong_password_here")
        print(f"Вхід '{test_username}' з неправильним паролем: {'успішно' if result_wrong else 'невдало'}")

    except FileNotFoundError as error:
        print(f"Файл не знайдено: {error}")
    except PermissionError as error:
        print(f"Немає доступу до файлу: {error}")
    except OSError as error:
        print(f"Помилка вводу-виводу: {error}")
    except ValidationError as error:
        print(f"Помилка валідації: {error}")
    except ValueError as error:
        print(f"Помилка значення: {error}")


if __name__ == "__main__":
    main()