"""Завдання 2 (варіант 8): фільтр та аналізатор журналів DNS-запитів."""

import argparse
import csv
import logging
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "data_v08"
DEFAULT_MIN_DOMAIN_LEN = 50
REQUIRED_COLUMNS = ("Timestamp", "ClientIP", "Domain", "QueryType")

LONG_LABEL_RE = re.compile(r"[a-z0-9-]{30,}")
SUSPICIOUS_TLD_RE = re.compile(r"\.(zip|top|xyz|click|tk|gq)$")

logger = logging.getLogger("dns_analyzer")


@dataclass
class DNSRecord:
    timestamp: datetime
    client_ip: str
    domain: str
    query_type: str
    reasons: list[str] = field(default_factory=list)


def load_blacklist(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as file:
        return {line.strip().lower() for line in file if line.strip()}


def read_dns_log(path: Path) -> Iterator[DNSRecord]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS) <= set(
            reader.fieldnames
        ):
            raise ValueError(
                f"{path}: очікуються колонки {', '.join(REQUIRED_COLUMNS)}"
            )
        for line_no, row in enumerate(reader, start=2):
            try:
                yield DNSRecord(
                    timestamp=datetime.fromisoformat(row["Timestamp"]),
                    client_ip=row["ClientIP"],
                    domain=row["Domain"].strip().lower(),
                    query_type=row["QueryType"].strip().upper(),
                )
            except (ValueError, AttributeError) as error:
                logger.warning("Line %d skipped: %s", line_no, error)


def detect_anomalies(
    record: DNSRecord, blacklist: set[str], min_domain_len: int
) -> list[str]:
    reasons = []
    if record.domain in blacklist:
        reasons.append("blacklisted")
    if LONG_LABEL_RE.search(record.domain):
        reasons.append("long subdomain")
    if match := SUSPICIOUS_TLD_RE.search(record.domain):
        reasons.append(f"suspicious TLD .{match.group(1)}")
    if len(record.domain) >= min_domain_len:
        reasons.append(f"length {len(record.domain)}")
    return reasons


def print_report(
    total: int, type_counter: Counter, suspicious: list[DNSRecord]
) -> None:
    print("\n=== Query Type Breakdown ===")
    for qtype, count in type_counter.most_common():
        print(f"{qtype:<5}: {count} ({count / total:.1%})")

    print("\n=== Suspicious DNS Activity ===")
    for rec in suspicious:
        tag = "BLACKMATCH" if "blacklisted" in rec.reasons else "DGA-DETECT"
        logger.warning(
            "[%s] Client %s queried %s (%s): %s",
            tag,
            rec.client_ip,
            rec.domain,
            rec.query_type,
            ", ".join(rec.reasons),
        )
    print()


def write_alerts_csv(path: Path, suspicious: list[DNSRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([*REQUIRED_COLUMNS, "Reasons"])
        for rec in suspicious:
            writer.writerow(
                [
                    rec.timestamp.isoformat(),
                    rec.client_ip,
                    rec.domain,
                    rec.query_type,
                    "; ".join(rec.reasons),
                ]
            )
    logger.info("Suspicious records exported to %s", path)


def positive_int(value: str) -> int:
    if not value.isdigit() or int(value) == 0:
        raise argparse.ArgumentTypeError(
            f"очікується ціле число > 0, отримано {value!r}"
        )
    return int(value)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dns-log",
        type=Path,
        default=DATA_DIR / "dns_queries.csv",
        help="CSV-журнал DNS-запитів",
    )
    parser.add_argument(
        "--blacklist",
        type=Path,
        default=DATA_DIR / "blacklist.txt",
        help="файл чорного списку",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=DATA_DIR / "dns_alerts.csv",
        help="CSV для аномальних запитів",
    )
    parser.add_argument(
        "--min-domain-len",
        type=positive_int,
        default=DEFAULT_MIN_DOMAIN_LEN,
        help=f"довжина домену, з якої він вважається аномальним (типово {DEFAULT_MIN_DOMAIN_LEN})",
    )


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout
    )


def run(args: argparse.Namespace) -> int:
    try:
        logger.info("Parsing DNS log file %s...", args.dns_log)
        blacklist = load_blacklist(args.blacklist)
        type_counter: Counter = Counter()
        suspicious = []
        for record in read_dns_log(args.dns_log):
            type_counter[record.query_type] += 1
            record.reasons = detect_anomalies(record, blacklist, args.min_domain_len)
            if record.reasons:
                suspicious.append(record)
        total = type_counter.total()
        logger.info("Processed %d DNS query records.", total)
        if total:
            print_report(total, type_counter, suspicious)
        write_alerts_csv(args.out_csv, suspicious)
    except (OSError, ValueError) as error:
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
