import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from labs.lab01 import task1, task2, task3


def main():
    print("=" * 50)
    print("Завдання 1: Аналізатор надійності паролів")
    print("=" * 50)
    task1.main()

    print("\n" + "=" * 50)
    print("Завдання 2: Система контролю доступу")
    print("=" * 50)
    task2.main()

    print("\n" + "=" * 50)
    print("Завдання 3: Хешування, CSV та JSON-логування")
    print("=" * 50)
    task3.main()


if __name__ == "__main__":
    main()