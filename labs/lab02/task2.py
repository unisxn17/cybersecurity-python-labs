"""Завдання 2 (варіант 8): фільтр та аналізатор журналів DNS-запитів."""

import argparse
import csv
import logging
import math
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "data_v08"
DEFAULT_DNS_LOG = DATA_DIR / "dns_queries.csv"
DEFAULT_BLACKLIST = DATA_DIR / "blacklist.txt"
DEFAULT_OUT_CSV = DATA_DIR / "dns_alerts.csv"
DEFAULT_MIN_DOMAIN_LEN = 50

REQUIRED_COLUMNS = ("Timestamp", "ClientIP", "Domain", "QueryType")
KNOWN_QUERY_TYPES = ("A", "AAAA", "TXT", "MX")

SUSPICIOUS_TLDS = ("zip", "top", "xyz", "click", "loan", "work", "gq", "tk", "ml", "cf")
SUSPICIOUS_TLD_RE = re.compile(rf"\.({'|'.join(SUSPICIOUS_TLDS)})$")
LONG_LABEL_RE = re.compile(r"(?:^|\.)([^.]{40,})(?:\.|$)")
DGA_LABEL_RE = re.compile(r"(?=[a-z0-9]*\d)(?=[a-z0-9]*[a-z])[a-z0-9]{12,}")
DGA_MIN_ENTROPY = 3.0
DOMAIN_RE = re.compile(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)+")

logger = logging.getLogger("dns_analyzer")


@dataclass
class DNSRecord:
    timestamp: datetime
    client_ip: str
    domain: str
    query_type: str
    reasons: list[str] = field(default_factory=list)


def shannon_entropy(text: str) -> float:
    counts = Counter(text)
    return -sum(n / len(text) * math.log2(n / len(text)) for n in counts.values())


def normalize_domain(domain: str) -> str:
    return domain.strip().lower().rstrip(".")


def load_blacklist(path: Path) -> set[str]:
    blacklist = set()
    with path.open(encoding="utf-8") as file:
        for line in file:
            entry = normalize_domain(line.split("#", 1)[0])
            if entry:
                blacklist.add(entry)
    logger.info("Loaded %d blacklisted domains from %s", len(blacklist), path)
    return blacklist


def read_dns_log(path: Path) -> Iterator[DNSRecord]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing = [
            col for col in REQUIRED_COLUMNS if col not in (reader.fieldnames or [])
        ]
        if missing:
            raise ValueError(f"У файлі {path} відсутні колонки: {', '.join(missing)}")
        for line_no, row in enumerate(reader, start=2):
            try:
                domain = normalize_domain(row["Domain"] or "")
                if not DOMAIN_RE.fullmatch(domain):
                    raise ValueError(f"некоректний домен {row['Domain']!r}")
                yield DNSRecord(
                    timestamp=datetime.fromisoformat(row["Timestamp"].strip()),
                    client_ip=row["ClientIP"].strip(),
                    domain=domain,
                    query_type=row["QueryType"].strip().upper(),
                )
            except (ValueError, AttributeError) as error:
                logger.warning("Line %d skipped: %s", line_no, error)


def is_blacklisted(domain: str, blacklist: set[str]) -> bool:
    parts = domain.split(".")
    return any(".".join(parts[i:]) in blacklist for i in range(len(parts)))


def detect_anomalies(
    record: DNSRecord, blacklist: set[str], min_domain_len: int
) -> list[str]:
    reasons = []
    domain = record.domain
    if is_blacklisted(domain, blacklist):
        reasons.append("BLACKMATCH")
    if len(domain) >= min_domain_len:
        reasons.append(f"LONG-DOMAIN({len(domain)})")
    if LONG_LABEL_RE.search(domain):
        reasons.append("LONG-SUBDOMAIN")
    labels = domain.split(".")[:-1]
    if any(
        DGA_LABEL_RE.fullmatch(lbl) and shannon_entropy(lbl) >= DGA_MIN_ENTROPY
        for lbl in labels
    ):
        reasons.append("DGA-DETECT")
    if tld_match := SUSPICIOUS_TLD_RE.search(domain):
        reasons.append(f"SUSPICIOUS-TLD(.{tld_match.group(1)})")
    if record.query_type == "TXT" and len(domain) >= min_domain_len:
        reasons.append("LONG-TXT")
    return reasons


def analyze(
    dns_log: Path, blacklist_path: Path, min_domain_len: int
) -> tuple[int, Counter, list[DNSRecord]]:
    logger.info("Parsing DNS log file %s...", dns_log)
    blacklist = load_blacklist(blacklist_path)
    total = 0
    type_counter: Counter = Counter()
    suspicious = []
    for record in read_dns_log(dns_log):
        total += 1
        type_counter[record.query_type] += 1
        record.reasons = detect_anomalies(record, blacklist, min_domain_len)
        if record.reasons:
            suspicious.append(record)
    logger.info("Processed %d DNS query records.", total)
    return total, type_counter, suspicious


def print_report(
    total: int, type_counter: Counter, suspicious: list[DNSRecord]
) -> None:
    print("\n=== Query Type Breakdown ===")
    for qtype in (
        *KNOWN_QUERY_TYPES,
        *sorted(set(type_counter) - set(KNOWN_QUERY_TYPES)),
    ):
        count = type_counter[qtype]
        share = count / total * 100 if total else 0.0
        print(f"{qtype:<5}: {count:,} ({share:.1f}%)")

    print("\n=== Suspicious DNS Activity ===")
    if not suspicious:
        print("No suspicious queries found.")
    for rec in suspicious:
        # один рядок на запит: тег за найвагомішою причиною, далі всі причини
        if "BLACKMATCH" in rec.reasons:
            line = f"[BLACKMATCH] Client {rec.client_ip} queried blacklisted domain: {rec.domain}"
        elif "LONG-TXT" in rec.reasons:
            line = f"[DGA-DETECT] Abnormally long TXT query domain: {rec.domain} (Length: {len(rec.domain)})"
        elif "DGA-DETECT" in rec.reasons:
            line = f"[DGA-DETECT] High entropy / suspicious subdomain: {rec.domain} (Client: {rec.client_ip})"
        else:
            line = (
                f"[SUSPICIOUS] Unusual domain: {rec.domain} (Client: {rec.client_ip})"
            )
        logger.warning("%s | %s", line, ", ".join(rec.reasons))
    print()


def write_alerts_csv(path: Path, suspicious: list[DNSRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([*REQUIRED_COLUMNS, "Length", "Reasons"])
        for rec in suspicious:
            writer.writerow(
                [
                    rec.timestamp.isoformat(),
                    rec.client_ip,
                    rec.domain,
                    rec.query_type,
                    len(rec.domain),
                    ";".join(rec.reasons),
                ]
            )
    logger.info("Suspicious records exported to %s", path)


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"очікується ціле число, отримано {value!r}"
        ) from None
    if number <= 0:
        raise argparse.ArgumentTypeError("значення має бути більше 0")
    return number


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dns-log", type=Path, default=DEFAULT_DNS_LOG, help="CSV-журнал DNS-запитів"
    )
    parser.add_argument(
        "--blacklist",
        type=Path,
        default=DEFAULT_BLACKLIST,
        help="файл чорного списку доменів",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=DEFAULT_OUT_CSV,
        help="CSV-файл для аномальних запитів",
    )
    parser.add_argument(
        "--min-domain-len",
        type=positive_int,
        default=DEFAULT_MIN_DOMAIN_LEN,
        help=f"мінімальна довжина домену, що вважається аномальною (типово {DEFAULT_MIN_DOMAIN_LEN})",
    )


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout
    )


def run(args: argparse.Namespace) -> int:
    for path in (args.dns_log, args.blacklist):
        if not path.is_file():
            logger.error("File not found: %s", path)
            return 1
    try:
        total, type_counter, suspicious = analyze(
            args.dns_log, args.blacklist, args.min_domain_len
        )
        print_report(total, type_counter, suspicious)
        write_alerts_csv(args.out_csv, suspicious)
    except (OSError, ValueError, csv.Error) as error:
        logger.error("%s", error)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Аналізатор журналів DNS-запитів (варіант 8)"
    )
    add_arguments(parser)
    setup_logging()
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
