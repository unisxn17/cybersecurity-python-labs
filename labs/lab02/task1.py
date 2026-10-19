"""Завдання 1: модель користувача, сеансу та журналу аудиту."""

import hashlib
import hmac
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import ClassVar

PBKDF2_ITERATIONS = 600_000
SALT_SIZE = 16
SESSION_TIMEOUT_SEC = 900

EMAIL_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9_]{2,63}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User:
    def __init__(
        self, username: str, email: str, role: str = "user", active: bool = True
    ):
        self.username = username
        self.email = email
        self.role = role
        self.active = active
        self.__password_hash: bytes | None = None
        self.__password_salt: bytes | None = None

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not isinstance(value, str) or not EMAIL_PATTERN.fullmatch(value):
            raise ValueError(f"Некоректний email: {value!r}")
        self._email = value

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )

    def set_password(self, password: str) -> None:
        if not password:
            raise ValueError("Пароль не може бути порожнім")
        self.__password_salt = os.urandom(SALT_SIZE)
        self.__password_hash = self._hash_password(password, self.__password_salt)

    def check_password(self, password: str) -> bool:
        if self.__password_hash is None or self.__password_salt is None:
            return False
        candidate = self._hash_password(password, self.__password_salt)
        return hmac.compare_digest(candidate, self.__password_hash)

    def deactivate(self) -> None:
        self.active = False

    def __str__(self) -> str:
        status = "active" if self.active else "inactive"
        return f"User({self.username}, {self.email}, role={self.role}, {status})"


class Admin(User):
    def __init__(
        self,
        username: str,
        email: str,
        permissions: Iterable[str] | None = None,
        active: bool = True,
    ):
        super().__init__(username, email, role="admin", active=active)
        self.permissions: set[str] = (
            set(permissions) if permissions is not None else set()
        )

    def grant_permission(self, permission: str) -> None:
        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def __str__(self) -> str:
        perms = ", ".join(sorted(self.permissions)) or "-"
        return f"{super().__str__()} permissions=[{perms}]"


class Session:
    def __init__(self, ip: str, login_time: datetime | None = None):
        self.ip = ip
        self.login_time = login_time or utc_now()
        self.last_activity = self.login_time

    def touch(self) -> None:
        self.last_activity = utc_now()

    def is_active(self, timeout_sec: int) -> bool:
        if timeout_sec <= 0:
            raise ValueError("timeout_sec має бути додатним")
        return utc_now() - self.last_activity < timedelta(seconds=timeout_sec)

    def __repr__(self) -> str:
        return (
            f"Session(ip={self.ip!r}, last_activity={self.last_activity.isoformat()})"
        )


@dataclass(frozen=True)
class AuditRecord:
    username: str
    action: str
    timestamp: datetime = field(default_factory=utc_now)

    def __str__(self) -> str:
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} UTC | {self.username:<10} | {self.action}"


class AuditLog:
    def __init__(self):
        self.records: list[AuditRecord] = []

    def add_log(self, username: str, action: str) -> AuditRecord:
        record = AuditRecord(username, action)
        self.records.append(record)
        return record

    def show_all(self) -> None:
        for record in self.records:
            print(record)


class UserAccount:
    # ключ -> (атрибут, допустимі типи); хеш і сіль пароля навмисно не доступні
    _ITEMS: ClassVar[dict[str, tuple[str, tuple[type, ...]]]] = {
        "user": ("user", (User,)),
        "session": ("session", (Session, type(None))),
        "audit_log": ("audit_log", (AuditLog,)),
    }

    def __init__(self, user: User, audit_log: AuditLog | None = None):
        self.user = user
        self.audit_log = audit_log if audit_log is not None else AuditLog()
        self.session: Session | None = None

    def login(self, username: str, password: str, ip: str) -> bool:
        if (
            username != self.user.username
            or not self.user.active
            or not self.user.check_password(password)
        ):
            self.audit_log.add_log(username, f"login_failure ip={ip}")
            return False
        self.session = Session(ip)
        self.session.touch()
        self.audit_log.add_log(username, f"login_success ip={ip}")
        return True

    def is_authenticated(self) -> bool:
        if self.session is None or not self.session.is_active(SESSION_TIMEOUT_SEC):
            return False
        self.session.touch()
        return True

    def logout(self) -> bool:
        if self.session is None:
            return False
        self.session = None
        self.audit_log.add_log(self.user.username, "logout")
        return True

    def __getitem__(self, key: str):
        if key not in self._ITEMS:
            raise KeyError(key)
        return getattr(self, self._ITEMS[key][0])

    def __setitem__(self, key: str, value) -> None:
        if key not in self._ITEMS:
            raise KeyError(key)
        attr, types = self._ITEMS[key]
        if not isinstance(value, types):
            raise TypeError(f"{key}: неправильний тип {type(value).__name__}")
        setattr(self, attr, value)
