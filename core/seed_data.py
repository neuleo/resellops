"""Seed script to populate ResellOps database with Leon's 14 historical Rebuy deals."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Union
from pathlib import Path

from core.database import init_db, create_deal, list_deals, get_pipeline_summary
from core.models import DealCreate, DealStatus


HISTORICAL_DEALS: List[DealCreate] = [
    # 1. Andrew
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Space Grau",
        seller_name="Andrew",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 7, 23),
        sell_date=date(2026, 8, 1),
        purchase_price_net=Decimal("400.00"),
        paypal_gross_amount=Decimal("410.57"),
        selling_price=Decimal("538.34"),
        notes="Rebuy Ankauf erfolgreich abgeschlossen.",
    ),
    # 2. S.E
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Polarstern",
        seller_name="S.E",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 7, 22),
        sell_date=date(2026, 8, 2),
        purchase_price_net=Decimal("480.00"),
        paypal_gross_amount=Decimal("492.62"),
        selling_price=Decimal("561.56"),
        rebuy_trn="TRN69928904",
        serial_number="L6003JVJ3Q",
        notes="Guter Zustand, Rebuy Ankauf verbucht.",
    ),
    # 3. Max Pfeufer (Storno / Erstattet)
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Space Grau",
        seller_name="Max Pfeufer",
        status=DealStatus.CANCELLED,
        buy_date=date(2026, 7, 28),
        sell_date=date(2026, 8, 5),
        purchase_price_net=Decimal("422.80"),
        paypal_gross_amount=Decimal("433.96"),
        selling_price=Decimal("433.96"),
        gross_margin=Decimal("0.00"),
        vat_25a=Decimal("0.00"),
        net_profit=Decimal("0.00"),
        rebuy_trn="TRN70071828",
        notes="Storno / 1:1 Erstattung ohne finanziellen Verlust.",
    ),
    # 4. Jan Groll
    DealCreate(
        product="MacBook Air 15 M2 8GB 256GB Silber",
        seller_name="Jan Groll",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 7, 28),
        sell_date=date(2026, 8, 8),
        purchase_price_net=Decimal("500.00"),
        paypal_gross_amount=Decimal("512.00"),
        selling_price=Decimal("564.09"),
        rebuy_trn="TRN69926118",
        serial_number="JR4DCQ4M1X",
        notes="MacBook Air 15 Zoll Ankauf Rebuy.",
    ),
    # 5. Isa
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Midnight",
        seller_name="Isa",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 8, 10),
        sell_date=date(2026, 8, 20),
        purchase_price_net=Decimal("550.00"),
        paypal_gross_amount=Decimal("564.40"),
        selling_price=Decimal("652.69"),
        dhl_tracking="239080130725",
        rebuy_trn="TRN70328869",
        serial_number="KG9VFKPXXK",
        notes="Sehr gepflegtes Midnight M2, Top-Marge.",
    ),
    # 6. Finn (Storno / Erstattet)
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Space Grau",
        seller_name="Finn",
        status=DealStatus.CANCELLED,
        buy_date=date(2026, 8, 12),
        sell_date=date(2026, 8, 18),
        purchase_price_net=Decimal("420.00"),
        paypal_gross_amount=Decimal("431.08"),
        selling_price=Decimal("431.08"),
        gross_margin=Decimal("0.00"),
        vat_25a=Decimal("0.00"),
        net_profit=Decimal("0.00"),
        notes="Transportschaden/Rückabwicklung, 1:1 PayPal Erstattung.",
    ),
    # 7. Daniel
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Midnight",
        seller_name="Daniel",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 8, 14),
        sell_date=date(2026, 8, 25),
        purchase_price_net=Decimal("550.00"),
        paypal_gross_amount=Decimal("564.40"),
        selling_price=Decimal("601.24"),
        dhl_tracking="239080134993",
        rebuy_trn="TRN70337521",
        notes="Abgeschlossen bei Rebuy.",
    ),
    # 8. Brandon
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Space Grau",
        seller_name="Brandon",
        status=DealStatus.IN_TRANSIT_OR_WAREHOUSE,
        buy_date=date(2026, 8, 15),
        purchase_price_net=Decimal("550.00"),
        paypal_gross_amount=Decimal("564.40"),
        selling_price=Decimal("640.00"),
        dhl_tracking="239080135422",
        rebuy_trn="TRN70338135",
        notes="Unterwegs zum Rebuy-Prüfzentrum.",
    ),
    # 9. Elias
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Midnight",
        seller_name="Elias",
        status=DealStatus.COMPLETED,
        buy_date=date(2026, 8, 20),
        sell_date=date(2026, 8, 31),
        purchase_price_net=Decimal("580.00"),
        paypal_gross_amount=Decimal("595.17"),
        selling_price=Decimal("696.79"),
        dhl_tracking="239080207089",
        rebuy_trn="TRN70461656",
        notes="Top-Zustand wie neu, maximale Rebuy Auszahlung.",
    ),
    # 10. Rene Patricio
    DealCreate(
        product="MacBook Air 13 M2 8GB 256GB Silber",
        seller_name="Rene Patricio",
        status=DealStatus.IN_TRANSIT_OR_WAREHOUSE,
        buy_date=date(2026, 8, 22),
        purchase_price_net=Decimal("550.00"),
        paypal_gross_amount=Decimal("564.40"),
        selling_price=Decimal("635.00"),
        dhl_tracking="239080220821",
        rebuy_trn="TRN70481512",
        notes="Paket eingeliefert, Tracking aktiv.",
    ),
    # 11. Thomas Mosch
    DealCreate(
        product="Mac Mini M2 8GB 256GB Silber",
        seller_name="Thomas Mosch",
        status=DealStatus.IN_TRANSIT_OR_WAREHOUSE,
        buy_date=date(2026, 8, 25),
        purchase_price_net=Decimal("320.00"),
        paypal_gross_amount=Decimal("329.00"),
        selling_price=Decimal("415.00"),
        dhl_tracking="239080239157",
        rebuy_trn="TRN70509006",
        notes="Mac Mini Desktop Deal.",
    ),
    # 12. Hannah (Storno / Erstattet)
    DealCreate(
        product='iPad Air 11" M2 128GB',
        seller_name="Hannah",
        status=DealStatus.CANCELLED,
        buy_date=date(2026, 8, 28),
        sell_date=date(2026, 9, 2),
        purchase_price_net=Decimal("370.00"),
        paypal_gross_amount=Decimal("379.81"),
        selling_price=Decimal("379.81"),
        gross_margin=Decimal("0.00"),
        vat_25a=Decimal("0.00"),
        net_profit=Decimal("0.00"),
        notes="Storno vor Versand, Erstattung 1:1 eingegangen.",
    ),
    # 13. Robin
    DealCreate(
        product="MacBook Air 15 M2 8GB 256GB Midnight",
        seller_name="Robin",
        status=DealStatus.PAID_WAITING_SHIPPING,
        buy_date=date(2026, 9, 2),
        purchase_price_net=Decimal("585.00"),
        paypal_gross_amount=Decimal("600.30"),
        selling_price=Decimal("685.00"),
        dhl_tracking="239080266893",
        rebuy_trn="TRN70555113",
        notes="Bezahlt, DHL-Label an Verkäufer übermittelt, wartet auf Versand.",
    ),
    # 14. CCl
    DealCreate(
        product='iPad Pro 11" M4 256GB Space Grau mit Apple Pencil Pro',
        seller_name="CCl",
        status=DealStatus.PAYPAL_PENDING,
        buy_date=date(2026, 9, 5),
        purchase_price_net=Decimal("750.00"),
        paypal_gross_amount=Decimal("769.51"),
        selling_price=Decimal("890.00"),
        notes="Zuschlag erteilt, PayPal-Zahlung in Vorbereitung.",
    ),
]


def seed_database(
    db_path: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> int:
    """Seeds the database with the 14 historical deals.

    Args:
        db_path: Target SQLite database file.
        force: If True, seeds even if deals already exist.

    Returns:
        Number of seeded deals.
    """
    init_db(db_path=db_path)
    existing_deals = list_deals(db_path=db_path)

    if existing_deals and not force:
        print(f"Database already contains {len(existing_deals)} deals. Skipping seed (use force=True to override).")
        return 0

    count = 0
    for deal_create in HISTORICAL_DEALS:
        create_deal(deal_create, db_path=db_path)
        count += 1

    print(f"Successfully seeded {count} deals into {db_path or 'default DB'}.")
    return count


if __name__ == "__main__":
    seed_database(force=True)
    summary = get_pipeline_summary()
    print("\n--- Pipeline Summary ---")
    print(f"Total Deals: {summary.total_deals}")
    print(f"Active: {summary.active_deals} | Completed: {summary.completed_deals} | Cancelled: {summary.cancelled_deals}")
    print(f"Status Breakdown: {summary.status_counts}")
    print(f"Total Spent: {summary.total_spent} €")
    print(f"Total Revenue: {summary.total_revenue} €")
    print(f"Total Gross Margin: {summary.total_gross_margin} €")
    print(f"Total Net Profit: {summary.total_net_profit} €")
