"""Database access layer and SQLite connection management for ResellOps.

Features:
- SQLite connection with WAL (Write-Ahead-Logging) mode
- PRAGMA foreign_keys = ON, busy_timeout = 5000
- Strong typed models via Pydantic v2
- Transactional CRUD operations
- Aggregate pipeline analytics
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from typing import Generator, List, Optional, Union, Dict, Any

from core.models import (
    Deal,
    DealBase,
    DealCreate,
    DealUpdate,
    DealStatus,
    PipelineSummary,
)
from core.calculator import (
    calculate_paypal_gross,
    calculate_margin_and_vat,
    _round_currency,
    _to_decimal,
)

DEFAULT_DB_PATH = Path(os.getenv("RESELLOPS_DB_PATH", "data/resellops.db"))


def _resolve_db_path(db_path: Optional[Union[str, Path]] = None) -> Path:
    """Resolves DB path and ensures parent directory exists."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db_connection(db_path: Optional[Union[str, Path]] = None) -> Generator[sqlite3.Connection, None, None]:
    """Provides a managed SQLite connection configured for high concurrency and safety."""
    path = _resolve_db_path(db_path)
    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # Configure safety & performance pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initializes the database schema and indexes."""
    with get_db_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                seller_name TEXT NOT NULL,
                status TEXT NOT NULL,
                buy_date TEXT,
                sell_date TEXT,
                purchase_price_net REAL,
                paypal_gross_amount REAL,
                selling_price REAL,
                gross_margin REAL,
                vat_25a REAL,
                net_profit REAL,
                rebuy_trn TEXT,
                dhl_tracking TEXT,
                serial_number TEXT,
                order_number TEXT,
                listing_url TEXT,
                seller_paypal_email TEXT,
                campaign_name TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
            CREATE INDEX IF NOT EXISTS idx_deals_rebuy_trn ON deals(rebuy_trn);
            CREATE INDEX IF NOT EXISTS idx_deals_seller ON deals(seller_name);
            CREATE INDEX IF NOT EXISTS idx_deals_buy_date ON deals(buy_date);
        """)

        # Ensure columns added in Phase 2 exist if upgrading existing DB
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(deals);")
        existing_cols = {col[1] for col in cursor.fetchall()}
        for col_name in ["listing_url", "seller_paypal_email", "campaign_name"]:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE deals ADD COLUMN {col_name} TEXT;")

        # Create campaign index after ensuring column exists
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_campaign ON deals(campaign_name);")


def _row_to_deal(row: sqlite3.Row) -> Deal:
    """Converts a SQLite row into a strongly typed Deal instance."""
    data = dict(row)
    
    # Decimal field conversion
    decimal_fields = [
        "purchase_price_net",
        "paypal_gross_amount",
        "selling_price",
        "gross_margin",
        "vat_25a",
        "net_profit",
    ]
    for field in decimal_fields:
        if data.get(field) is not None:
            data[field] = Decimal(str(data[field]))
        else:
            data[field] = None

    # Date field conversion
    if data.get("buy_date"):
        data["buy_date"] = date.fromisoformat(data["buy_date"])
    if data.get("sell_date"):
        data["sell_date"] = date.fromisoformat(data["sell_date"])

    # Datetime field conversion
    if data.get("created_at"):
        data["created_at"] = datetime.fromisoformat(data["created_at"])
    if data.get("updated_at"):
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])

    return Deal(**data)


def create_deal(
    deal_input: Union[DealCreate, dict],
    db_path: Optional[Union[str, Path]] = None,
) -> Deal:
    """Inserts a new deal into the database and returns the persisted Deal."""
    if isinstance(deal_input, dict):
        deal = DealCreate(**deal_input)
    else:
        deal = deal_input

    now_iso = datetime.now(timezone.utc).isoformat()
    buy_date_iso = deal.buy_date.isoformat() if deal.buy_date else None
    sell_date_iso = deal.sell_date.isoformat() if deal.sell_date else None

    query = """
        INSERT INTO deals (
            product, seller_name, status, buy_date, sell_date,
            purchase_price_net, paypal_gross_amount, selling_price,
            gross_margin, vat_25a, net_profit,
            rebuy_trn, dhl_tracking, serial_number, order_number, notes,
            listing_url, seller_paypal_email, campaign_name,
            created_at, updated_at
        ) VALUES (
            :product, :seller_name, :status, :buy_date, :sell_date,
            :purchase_price_net, :paypal_gross_amount, :selling_price,
            :gross_margin, :vat_25a, :net_profit,
            :rebuy_trn, :dhl_tracking, :serial_number, :order_number, :notes,
            :listing_url, :seller_paypal_email, :campaign_name,
            :created_at, :updated_at
        )
    """

    params = {
        "product": deal.product,
        "seller_name": deal.seller_name,
        "status": deal.status.value if isinstance(deal.status, DealStatus) else str(deal.status),
        "buy_date": buy_date_iso,
        "sell_date": sell_date_iso,
        "purchase_price_net": float(deal.purchase_price_net) if deal.purchase_price_net is not None else None,
        "paypal_gross_amount": float(deal.paypal_gross_amount) if deal.paypal_gross_amount is not None else None,
        "selling_price": float(deal.selling_price) if deal.selling_price is not None else None,
        "gross_margin": float(deal.gross_margin) if deal.gross_margin is not None else None,
        "vat_25a": float(deal.vat_25a) if deal.vat_25a is not None else None,
        "net_profit": float(deal.net_profit) if deal.net_profit is not None else None,
        "rebuy_trn": deal.rebuy_trn,
        "dhl_tracking": deal.dhl_tracking,
        "serial_number": deal.serial_number,
        "order_number": deal.order_number,
        "notes": deal.notes,
        "listing_url": deal.listing_url,
        "seller_paypal_email": deal.seller_paypal_email,
        "campaign_name": deal.campaign_name,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        new_id = cursor.lastrowid

    if new_id is None:
        raise RuntimeError("Database did not return a valid lastrowid after deal insert.")

    retrieved = get_deal(new_id, db_path=db_path)
    if retrieved is None:
        raise RuntimeError(f"Failed to retrieve deal after creation (id={new_id})")
    return retrieved


def get_deal(
    deal_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Deal]:
    """Retrieves a single deal by its primary key ID."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_deal(row)


def get_deal_by_trn(
    rebuy_trn: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Deal]:
    """Retrieves a deal by Rebuy transaction reference (TRN)."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deals WHERE rebuy_trn = ?", (rebuy_trn,))
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_deal(row)


def update_deal(
    deal_id: int,
    updates: Union[DealUpdate, dict],
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Deal]:
    """Updates an existing deal with partial fields and recalculates financials if needed."""
    current = get_deal(deal_id, db_path=db_path)
    if not current:
        return None

    update_dict = updates.model_dump(exclude_unset=True) if isinstance(updates, DealUpdate) else dict(updates)
    if not update_dict:
        return current

    # Merge current with updates to recheck financial consistency
    new_status = update_dict.get("status", current.status)
    if isinstance(new_status, DealStatus):
        new_status = new_status.value

    purchase_price_net = update_dict.get("purchase_price_net", current.purchase_price_net)
    paypal_gross_amount = update_dict.get("paypal_gross_amount", current.paypal_gross_amount)
    selling_price = update_dict.get("selling_price", current.selling_price)

    # Auto-calculate PayPal gross if net was updated but gross was not supplied
    if "purchase_price_net" in update_dict and "paypal_gross_amount" not in update_dict:
        if purchase_price_net is not None:
            paypal_gross_amount = calculate_paypal_gross(purchase_price_net)
            update_dict["paypal_gross_amount"] = paypal_gross_amount

    # Financial recalculation if prices or status changed and explicit margins were not provided
    effective_cost = paypal_gross_amount if paypal_gross_amount is not None else purchase_price_net
    if "gross_margin" not in update_dict and effective_cost is not None and selling_price is not None:
        if new_status == DealStatus.CANCELLED.value:
            update_dict["gross_margin"] = Decimal("0.00")
            update_dict["vat_25a"] = Decimal("0.00")
            update_dict["net_profit"] = Decimal("0.00")
        else:
            calc = calculate_margin_and_vat(effective_cost, selling_price)
            update_dict["gross_margin"] = calc.gross_margin
            update_dict["vat_25a"] = calc.vat_25a
            update_dict["net_profit"] = calc.net_profit

    # Build SET clause
    fields = []
    params: Dict[str, Any] = {"id": deal_id}
    now_iso = datetime.now(timezone.utc).isoformat()
    update_dict["updated_at"] = now_iso

    for key, val in update_dict.items():
        fields.append(f"{key} = :{key}")
        if isinstance(val, (date, datetime)):
            params[key] = val.isoformat()
        elif isinstance(val, Decimal):
            params[key] = float(val)
        elif isinstance(val, DealStatus):
            params[key] = val.value
        else:
            params[key] = val

    set_clause = ", ".join(fields)
    sql = f"UPDATE deals SET {set_clause} WHERE id = :id"

    with get_db_connection(db_path) as conn:
        conn.execute(sql, params)

    return get_deal(deal_id, db_path=db_path)


def delete_deal(
    deal_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Deletes a deal by ID. Returns True if a record was deleted."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
        return cursor.rowcount > 0


def list_deals(
    status: Optional[Union[DealStatus, str]] = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Deal]:
    """Returns a list of deals, optionally filtered by status, sorted by id ASC."""
    sql = "SELECT * FROM deals"
    params: List[Any] = []

    if status:
        stat_val = status.value if isinstance(status, DealStatus) else str(status)
        sql += " WHERE status = ?"
        params.append(stat_val)

    sql += " ORDER BY id ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [_row_to_deal(r) for r in rows]


def get_pipeline_summary(
    db_path: Optional[Union[str, Path]] = None,
) -> PipelineSummary:
    """Computes comprehensive pipeline metrics and financial aggregations across all deals."""
    summary = PipelineSummary()

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Status counts
        cursor.execute("SELECT status, COUNT(*) as cnt FROM deals GROUP BY status")
        counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}
        summary.status_counts = counts
        summary.total_deals = sum(counts.values())

        summary.completed_deals = counts.get(DealStatus.COMPLETED.value, 0)
        summary.cancelled_deals = counts.get(DealStatus.CANCELLED.value, 0)
        summary.active_deals = summary.total_deals - (summary.completed_deals + summary.cancelled_deals)

        # Financial sums
        cursor.execute("""
            SELECT
                SUM(COALESCE(paypal_gross_amount, purchase_price_net, 0)) as total_spent,
                SUM(COALESCE(selling_price, 0)) as total_revenue,
                SUM(COALESCE(gross_margin, 0)) as total_gross_margin,
                SUM(COALESCE(vat_25a, 0)) as total_vat_25a,
                SUM(COALESCE(net_profit, 0)) as total_net_profit
            FROM deals
        """)
        row = cursor.fetchone()
        if row:
            summary.total_spent = _round_currency(Decimal(str(row["total_spent"] or 0)))
            summary.total_revenue = _round_currency(Decimal(str(row["total_revenue"] or 0)))
            summary.total_gross_margin = _round_currency(Decimal(str(row["total_gross_margin"] or 0)))
            summary.total_vat_25a = _round_currency(Decimal(str(row["total_vat_25a"] or 0)))
            summary.total_net_profit = _round_currency(Decimal(str(row["total_net_profit"] or 0)))

        # Active capital tied & expected net profit (active deals)
        cursor.execute("""
            SELECT
                SUM(COALESCE(paypal_gross_amount, purchase_price_net, 0)) as active_capital,
                SUM(COALESCE(net_profit, 0)) as expected_net_profit
            FROM deals
            WHERE status NOT IN ('COMPLETED', 'CANCELLED')
        """)
        active_row = cursor.fetchone()
        if active_row:
            summary.active_capital_tied = _round_currency(Decimal(str(active_row["active_capital"] or 0)))
            summary.expected_net_profit = _round_currency(Decimal(str(active_row["expected_net_profit"] or 0)))

        # Realized net profit (completed deals)
        cursor.execute("""
            SELECT
                SUM(COALESCE(net_profit, 0)) as realized_net_profit
            FROM deals
            WHERE status = 'COMPLETED'
        """)
        comp_row = cursor.fetchone()
        if comp_row:
            summary.realized_net_profit = _round_currency(Decimal(str(comp_row["realized_net_profit"] or 0)))

    return summary


def get_pending_payments(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Deal]:
    """Retrieves all deals waiting for PayPal payment (status == PAYPAL_PENDING)."""
    return list_deals(status=DealStatus.PAYPAL_PENDING, db_path=db_path)
