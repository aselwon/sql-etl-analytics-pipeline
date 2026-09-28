from decimal import Decimal
import os

import pytest

from shoppulse.pipeline import ROOT, HEADERS, connect, ingest, transform, check_data, read_csv


def test_fixture_headers_and_row_counts():
    assert len(read_csv(ROOT / "data/raw/orders.csv", HEADERS["orders"])) == 8


@pytest.mark.parametrize("content", ["wrong\n1\n", "a,b\n", "a,b\n1\n"])
def test_reject_malformed_csv(tmp_path, content):
    source = tmp_path / "bad.csv"
    source.write_text(content)
    with pytest.raises(ValueError):
        read_csv(source, ["a", "b"])


def test_blank_cells_are_null(tmp_path):
    source = tmp_path / "blank.csv"
    source.write_text("a,b\n1, \n")
    assert read_csv(source, ["a", "b"]) == [("1", None)]


@pytest.fixture
def db():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL required for PostgreSQL integration tests")
    with connect() as conn:
        # Integration tests never commit fixture replacements to a running demo.
        conn.execute("SELECT pg_advisory_xact_lock(726410)")
        try:
            yield conn
        finally:
            conn.rollback()


def test_pipeline_idempotent_and_kpis(db):
    for _ in range(2):
        ingest(db, ROOT / "data/raw")
        transform(db)
        check_data(db)
        assert db.execute("SELECT * FROM marts.kpis").fetchone() == (
            Decimal("127.00"), 6, 3, Decimal("21.17"), 2, 12)
    assert db.execute("SELECT revenue FROM marts.daily_revenue WHERE day='2025-01-05'").fetchone()[0] == 45
    assert db.execute("SELECT revenue FROM marts.top_products WHERE product_id=1").fetchone()[0] == 50
    assert db.execute("SELECT retention_rate FROM marts.cohort_retention WHERE cohort_month='2025-01-01' AND month_number=1").fetchone()[0] == Decimal("0.5000")


def test_bad_data_fails_and_preserves_published_marts(db):
    ingest(db, ROOT / "data/raw")
    transform(db)
    ingest(db, ROOT / "data/bad")
    with pytest.raises(ValueError, match="010_not_null.*020_unique.*030_revenue.*040_references"):
        check_data(db)
    with pytest.raises(ValueError):
        transform(db)
    assert db.execute("SELECT revenue FROM marts.kpis").fetchone()[0] == 127


def test_invalid_type_rolls_back_ingestion(db, tmp_path):
    ingest(db, ROOT / "data/raw")
    for name in HEADERS:
        (tmp_path / f"{name}.csv").write_text((ROOT / f"data/raw/{name}.csv").read_text())
    (tmp_path / "items.csv").write_text("order_id,product_id,product_name,quantity,unit_price\n101,1,Coffee,oops,10.00\n")
    import psycopg
    with pytest.raises(psycopg.Error):
        ingest(db, tmp_path)
    assert db.execute("SELECT COUNT(*) FROM raw.orders").fetchone()[0] == 8


def test_no_completed_orders_has_zero_kpis(db):
    ingest(db, ROOT / "data/raw")
    db.execute("UPDATE raw.orders SET status='cancelled'")
    transform(db)
    assert db.execute("SELECT * FROM marts.kpis").fetchone() == (0, 0, 0, 0, 0, 0)
    assert db.execute("SELECT COUNT(*) FROM marts.cohort_retention").fetchone()[0] == 0


def test_cohort_months_cross_year_boundary(db):
    ingest(db, ROOT / "data/raw")
    db.execute("UPDATE raw.orders SET order_date='2024-12-01' WHERE order_id=101")
    transform(db)
    assert db.execute("SELECT retention_rate FROM marts.cohort_retention WHERE cohort_month='2024-12-01' AND month_number=2").fetchone()[0] == 1
