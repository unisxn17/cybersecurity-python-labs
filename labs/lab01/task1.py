import os
import random
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

passwords = [
    "ThreatH@nt3r", "weak123", "P3n3trat10n@Test", "visitor",
    "Cyber@Defense2023", "normal", "Incident@R3sp0nse", "standard",
    "Risk@Analys1s", "typical",
]

criteria = {
    "min_length": 10,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}

forbidden_passwords = {"weak123", "visitor", "normal", "standard", "typical", "admin"}


def add_duplicates(password_list):

    duplicates = [random.choice(password_list) for i in range(3)]
    # print(duplicates)
    return password_list + duplicates


def assess_password(password, min_length, all_passwords):

    if password in forbidden_passwords or len(password) < min_length:
        return "Заборонений"

    has_digit = any(c.isdigit() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_special = any(not c.isalnum() for c in password)

    groups_met = sum([has_digit, has_upper, has_lower, has_special])
    meets_all_required = has_digit and has_upper and has_special

    if meets_all_required:
        is_long_enough = len(password) >= min_length + 4
        is_unique = all_passwords.count(password) == 1
        if is_long_enough and is_unique:
            return "Дуже сильний"
        return "Сильний"

    if groups_met >= 2:
        return "Середній"

    return "Слабкий"


def analyze_passwords(password_list, min_length):

    results = []
    for password in password_list:
        strength = assess_password(password, min_length, password_list)
        results.append((password, strength))
    return results


def print_results(results):

    for password, strength in results:
        print(f"{password:<20} --> {strength:<15}")


def main():
    print(f"{STUDENT_NAME}, {GROUP_NAME}, Варіант: {VARIANT_NUMBER}")
    full_list = add_duplicates(passwords)
    # print(full_list)
    results = analyze_passwords(full_list, criteria["min_length"])
    print_results(results)


if __name__ == "__main__":
    main()