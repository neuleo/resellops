"""ResellOps Core Package

Core database models, calculation engines, and seed scripts.
"""

from .calculator import (
    calculate_margin_and_vat,
    calculate_paypal_gross,
    calculate_paypal_fee,
    calculate_paypal_net,
    MarginResult,
)
from .models import Deal, DealCreate, DealUpdate, DealStatus
from .database import (
    init_db,
    get_db_connection,
    create_deal,
    get_deal,
    update_deal,
    delete_deal,
    list_deals,
    get_pipeline_summary,
)

__all__ = [
    "calculate_margin_and_vat",
    "calculate_paypal_gross",
    "calculate_paypal_fee",
    "calculate_paypal_net",
    "MarginResult",
    "Deal",
    "DealCreate",
    "DealUpdate",
    "DealStatus",
    "init_db",
    "get_db_connection",
    "create_deal",
    "get_deal",
    "update_deal",
    "delete_deal",
    "list_deals",
    "get_pipeline_summary",
]
