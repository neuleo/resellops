"""Unit tests for ResellOps database layer (core.database & core.models)."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import pytest

from core.database import (
    init_db,
    get_db_connection,
    create_deal,
    get_deal,
    get_deal_by_trn,
    update_deal,
    delete_deal,
    list_deals,
    get_pipeline_summary,
)
from core.models import DealStatus, DealCreate, DealUpdate
from core.seed_data import seed_database, HISTORICAL_DEALS


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing an isolated SQLite database path."""
    db_file = tmp_path / "test_resellops.db"
    init_db(db_file)
    return db_file


def test_init_db_and_wal_mode(db_path: Path):
    """Verifies that DB initializes properly with WAL mode and indices."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.lower() == "wal"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deals';")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_deals_status';")
        assert cursor.fetchone() is not None


def test_create_deal_with_auto_calculation(db_path: Path):
    """Creating a deal with net price and selling price automatically calculates gross and margins."""
    deal_payload = DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Midnight",
        seller_name="Isa",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 8, 10),
        sell_date=date(2026, 8, 20),
        purchase_price_net=Decimal("550.00"),
        selling_price=Decimal("652.69"),
        rebuy_trn="TRN70328869",
        serial_number="KG9VFKPXXK",
    )

    created = create_deal(deal_payload, db_path=db_path)
    assert created.id is not None
    assert created.paypal_gross_amount == Decimal("564.40")
    assert created.gross_margin == Decimal("88.29")
    assert created.vat_25a in (Decimal("14.09"), Decimal("14.10"))
    assert created.gross_margin is not None and created.vat_25a is not None
    assert created.net_profit == created.gross_margin - created.vat_25a
    assert created.rebuy_trn == "TRN70328869"


def test_get_deal_and_get_by_trn(db_path: Path):
    """Verifies retrieval by ID and by Rebuy TRN."""
    deal_payload = DealCreate(
        product="Mac Mini M2 8GB 256GB Silber",
        seller_name="Thomas Mosch",
        status=DealStatus.IN_TRANSIT_OR_WAREHOUSE,
        purchase_price_net=Decimal("320.00"),
        rebuy_trn="TRN70509006",
    )
    created = create_deal(deal_payload, db_path=db_path)

    by_id = get_deal(created.id, db_path=db_path)
    assert by_id is not None
    assert by_id.seller_name == "Thomas Mosch"

    by_trn = get_deal_by_trn("TRN70509006", db_path=db_path)
    assert by_trn is not None
    assert by_trn.id == created.id

    assert get_deal(999999, db_path=db_path) is None
    assert get_deal_by_trn("NON_EXISTENT", db_path=db_path) is None


def test_update_deal_lifecycle(db_path: Path):
    """Tests updating a deal from PAYPAL_PENDING to IN_TRANSIT to COMPLETED."""
    initial = create_deal(
        DealCreate(
            product="iPad Pro 11 M4",
            seller_name="CCl",
            status=DealStatus.PAYPAL_PENDING,
            purchase_price_net=Decimal("750.00"),
        ),
        db_path=db_path,
    )

    # 1. Update with tracking number and move to IN_TRANSIT
    updated_1 = update_deal(
        initial.id,
        DealUpdate(
            status=DealStatus.IN_TRANSIT_OR_WAREHOUSE,
            dhl_tracking="239080999999",
            rebuy_trn="TRN70999999",
        ),
        db_path=db_path,
    )
    assert updated_1 is not None
    assert updated_1.status == DealStatus.IN_TRANSIT_OR_WAREHOUSE
    assert updated_1.dhl_tracking == "239080999999"
    assert updated_1.rebuy_trn == "TRN70999999"

    # 2. Mark completed with selling price -> should automatically compute margin and VAT
    updated_2 = update_deal(
        initial.id,
        DealUpdate(
            status=DealStatus.COMPLETED,
            selling_price=Decimal("890.00"),
            sell_date=date(2026, 9, 10),
        ),
        db_path=db_path,
    )
    assert updated_2 is not None
    assert updated_2.status == DealStatus.COMPLETED
    assert updated_2.selling_price == Decimal("890.00")
    # Gross EK was 769.51. Margin = 890.00 - 769.51 = 120.49
    assert updated_2.gross_margin == Decimal("120.49")
    assert updated_2.vat_25a is not None
    assert updated_2.net_profit is not None


def test_delete_deal(db_path: Path):
    """Verifies deleting a deal."""
    deal = create_deal(
        DealCreate(product="Temp Item", seller_name="Temp Seller"),
        db_path=db_path,
    )
    assert delete_deal(deal.id, db_path=db_path) is True
    assert get_deal(deal.id, db_path=db_path) is None
    assert delete_deal(deal.id, db_path=db_path) is False


def test_list_deals_and_filtering(db_path: Path):
    """Verifies listing deals and status filtering."""
    create_deal(DealCreate(product="Item 1", seller_name="A", status=DealStatus.COMPLETED), db_path=db_path)
    create_deal(DealCreate(product="Item 2", seller_name="B", status=DealStatus.COMPLETED), db_path=db_path)
    create_deal(DealCreate(product="Item 3", seller_name="C", status=DealStatus.IN_TRANSIT_OR_WAREHOUSE), db_path=db_path)

    all_deals = list_deals(db_path=db_path)
    assert len(all_deals) == 3

    completed = list_deals(status=DealStatus.COMPLETED, db_path=db_path)
    assert len(completed) == 2

    transit = list_deals(status=DealStatus.IN_TRANSIT_OR_WAREHOUSE, db_path=db_path)
    assert len(transit) == 1

    # Pagination
    page_1 = list_deals(limit=2, offset=0, db_path=db_path)
    assert len(page_1) == 2
    page_2 = list_deals(limit=2, offset=2, db_path=db_path)
    assert len(page_2) == 1


def test_seed_database_and_pipeline_summary(db_path: Path):
    """Verifies that seed_database imports exactly 14 deals and produces accurate KPI aggregations."""
    seeded_count = seed_database(db_path=db_path)
    assert seeded_count == 14
    assert len(HISTORICAL_DEALS) == 14

    # Running again without force should skip
    seeded_again = seed_database(db_path=db_path, force=False)
    assert seeded_again == 0

    deals = list_deals(db_path=db_path)
    assert len(deals) == 14

    summary = get_pipeline_summary(db_path=db_path)
    assert summary.total_deals == 14
    assert summary.completed_deals == 6
    assert summary.cancelled_deals == 3
    assert summary.active_deals == 5  # 14 - 6 - 3 = 5

    # Check key financial assertions
    assert summary.total_spent > Decimal("0.00")
    assert summary.total_revenue > Decimal("0.00")
    assert summary.total_gross_margin > Decimal("0.00")
    assert summary.total_vat_25a > Decimal("0.00")
    assert summary.total_net_profit > Decimal("0.00")
