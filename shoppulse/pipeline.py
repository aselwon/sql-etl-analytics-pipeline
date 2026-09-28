"""Transactional full-snapshot ingestion and ordered SQL orchestration."""

import argparse
import csv
import os
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {
    "customers": ["customer_id", "customer_name", "signup_date"],
    "orders": ["order_id", "customer_id", "order_date", "status"],
    "items": ["order_id", "product_id", "product_name", "quantity", "unit_price"],
}


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"])


def read_csv(path, headers):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        if next(reader, None) != headers:
            raise ValueError(f"Unexpected CSV header: {path}; expected {headers}")
        rows = list(reader)
        if not rows:
            raise ValueError(f"Empty source: {path}")
        for line, row in enumerate(rows, 2):
            if len(row) != len(headers):
                raise ValueError(f"Wrong column count: {path}:{line}")
        return [tuple(value.strip() or None for value in row) for row in rows]


def execute_file(conn, path):
    conn.execute(path.read_text())


def ingest(conn, data_dir):
    # Validate all input files before modifying the database. COPY and replacement
    # share one transaction, so malformed values preserve the previous snapshot.
    sources = {name: read_csv(Path(data_dir) / f"{name}.csv", fields)
               for name, fields in HEADERS.items()}
    with conn.transaction():
        execute_file(conn, ROOT / "sql/001_raw.sql")
        conn.execute("TRUNCATE raw.customers, raw.orders, raw.items")
        for name, rows in sources.items():
            with conn.cursor().copy(sql.SQL("COPY raw.{} FROM STDIN").format(sql.Identifier(name))) as copy:
                for row in rows:
                    copy.write_row(row)
    print("Ingested " + ", ".join(f"{name}={len(rows)}" for name, rows in sources.items()))


def check_data(conn):
    failures = []
    for path in sorted((ROOT / "sql/tests").glob("*.sql")):
        count = conn.execute(path.read_text()).fetchone()[0]
        print(f"{'FAIL' if count else 'PASS'} {path.stem}: {count} violations")
        if count:
            failures.append(path.stem)
    if failures:
        raise ValueError("Data quality failed: " + ", ".join(failures))


def transform(conn):
    with conn.transaction():
        # Never publish new marts from an invalid raw snapshot.
        check_data(conn)
        for path in sorted((ROOT / "sql/models").glob("*.sql")):
            execute_file(conn, path)
    print("Published staging and marts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["ingest", "transform", "test-data", "run"])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw")
    args = parser.parse_args()
    try:
        with connect() as conn:
            # Serialize runners to avoid concurrent snapshot replacement.
            conn.execute("SELECT pg_advisory_xact_lock(726410)")
            if args.command in ("ingest", "run"):
                ingest(conn, args.data_dir)
            if args.command in ("transform", "run"):
                transform(conn)
            if args.command in ("test-data", "run"):
                check_data(conn)
    except (ValueError, psycopg.Error, OSError, KeyError) as exc:
        parser.exit(1, f"Pipeline failed: {exc}\n")
