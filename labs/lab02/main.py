"""Лабораторна робота №2: команди demo (Завдання 1) та analyze (Завдання 2)."""

import argparse
import sys
from datetime import timedelta

from labs.lab02 import task2
from labs.lab02.task1 import (
    SESSION_TIMEOUT_SEC,
    Admin,
    AuditLog,
    Session,
    User,
    UserAccount,
)
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def demo() -> int:
    print(f"{STUDENT_NAME}, {GROUP_NAME}, варіант {VARIANT_NUMBER}")
    audit = AuditLog()

    section("Створення користувача")
    alice = User("alice", "alice@example.com")
    alice.set_password("Str0ngP@ssword1")
    print(alice)
    account = UserAccount(alice, audit)

    section("Невдалий і успішний вхід")
    print("Неправильний пароль:", account.login("alice", "wrong-password", "10.0.0.10"))
    print(
        "Правильний пароль:  ", account.login("alice", "Str0ngP@ssword1", "10.0.0.10")
    )
    print("Автентифіковано:    ", account.is_authenticated())

    section("Зміна email із валідацією")
    for new_email in (
        "alice_work@corp.example.org",
        "1bad@example.com",
        "al@example.com",
        "alice@localhost",
    ):
        try:
            alice.email = new_email
            print(f"OK    {new_email} -> {alice.email}")
        except ValueError as error:
            print(f"ERROR {error}")

    section("Права адміністратора")
    admin = Admin("root_admin", "root_admin@example.com", permissions=["read_logs"])
    admin.grant_permission("manage_users")
    admin.grant_permission("delete_logs")
    admin.revoke_permission("delete_logs")
    print(admin)
    print("has manage_users:", admin.has_permission("manage_users"))
    print("has delete_logs: ", admin.has_permission("delete_logs"))

    section("Доступ через __getitem__ / __setitem__")
    print("account['user']:", account["user"])
    for key, value in (("password_hash", None), ("session", "not-a-session")):
        try:
            account[key] if value is None else account.__setitem__(key, value)
        except (KeyError, TypeError) as error:
            print(f"{type(error).__name__}: {error}")

    section("Завершення сеансу за таймаутом")
    account["session"].last_activity -= timedelta(seconds=SESSION_TIMEOUT_SEC + 1)
    print("Автентифіковано після простою:", account.is_authenticated())
    try:
        Session("10.0.0.10").is_active(0)
    except ValueError as error:
        print(f"ValueError: {error}")

    section("Вихід із системи та деактивація")
    account.login("alice", "Str0ngP@ssword1", "10.0.0.11")
    print("Вихід:", account.logout())
    alice.deactivate()
    print(
        "Вхід деактивованого користувача:",
        account.login("alice", "Str0ngP@ssword1", "10.0.0.11"),
    )

    section("Записи AuditLog")
    audit.show_all()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Лабораторна робота №2")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("demo", help="демонстрація класів Завдання 1")
    analyze_parser = subparsers.add_parser(
        "analyze", help="аналізатор DNS-запитів (Завдання 2)"
    )
    task2.add_arguments(analyze_parser)

    args = parser.parse_args(argv)
    if args.command == "demo":
        return demo()
    task2.setup_logging()
    return task2.run(args)


if __name__ == "__main__":
    sys.exit(main())
