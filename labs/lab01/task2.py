import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

users = {
    "crypto_specialist": {"role": "cryptographer", "clearance": 4, "department": "Cryptography", "active": True},
    "privacy_officer": {"role": "privacy_analyst", "clearance": 3, "department": "Privacy", "active": True},
    "data_scientist": {"role": "data_analyst", "clearance": 2, "department": "Analytics", "active": True},
    "field_engineer": {"role": "field_support", "clearance": 2, "department": "Field Ops", "active": True},
    "test_account": {"role": "testing", "clearance": 1, "department": "QA", "active": False},
}

resources = [
    ("encryption_keys", 4), ("privacy_policies", 3), ("anonymized_data", 2),
    ("field_reports", 2), ("crypto_algorithms", 4), ("consent_forms", 1),
    ("data_classification", 3), ("key_management", 4), ("statistical_models", 2),
    ("public_datasets", 1),
]

security_levels = ("Unclassified", "For Official Use", "Confidential", "Secret")
blocked_users = {"test_account", "gdpr_violation", "data_breach_user"}


def resource_level_name(level):
    return security_levels[level - 1]


def print_resources():
    print("Ресурси системи:")
    for name, level in resources:
        print(f"  {name} -> {resource_level_name(level)}")


def check_access(username, resource_level):
    if username not in users:
        return False, "User not found"

    if username in blocked_users:
        return False, "User is blocked"

    user = users[username]

    if not user["active"]:
        return False, "Account inactive"

    if user["clearance"] < resource_level:
        return False, "Insufficient clearance"

    return True, ""


def check_all_access():
    results = []
    for username in users:
        for resource_name, resource_level in resources:
            allowed, reason = check_access(username, resource_level)
            results.append((username, resource_name, allowed, reason))
    return results


def print_access_results(results):
    for username, resource_name, allowed, reason in results:
        status = "ALLOW" if allowed else f"DENY ({reason})"
        print(f"user={username} resource={resource_name} -> {status}")


def main():
    print(f"{STUDENT_NAME}, {GROUP_NAME}, Варіант: {VARIANT_NUMBER}")
    print_resources()
    print()
    results = check_all_access()
    print_access_results(results)


if __name__ == "__main__":
    main()