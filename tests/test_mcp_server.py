"""
Unit tests for the ResellOps MCP Server Tools.
"""

from decimal import Decimal
import pytest
from core.database import init_db
from server_mcp import (
    resellops_create_deal,
    resellops_update_deal_status,
    resellops_record_rebuy_payout,
    resellops_get_pending_payments,
    resellops_get_pipeline_summary,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Isolate database tests in temporary directory."""
    test_db = tmp_path / "test_mcp.db"
    init_db(test_db)
    monkeypatch.setattr("core.database.DEFAULT_DB_PATH", test_db)
    monkeypatch.setattr("server_mcp.init_db", lambda: None)


def test_mcp_create_deal_flow():
    # Test creating a deal with negotiated net price
    res = resellops_create_deal(
        product="MacBook Air M1 256GB Space Grau",
        seller_name="Peter",
        listing_url="https://kleinanzeigen.de/s-anzeige/123",
        agreed_price_net=270.0,
        seller_paypal_email="peter@example.com",
        campaign_name="macbook_air_m1_lowball",
        notes="Guter Zustand, Akku 92%"
    )
    assert "✅ Deal #" in res
    assert "270.00 €" in res
    # 270 net -> PayPal gross: (270 + 0.35) / (1 - 0.0249) = 277.25
    assert "277.25 €" in res
    assert "PAYPAL_PENDING" in res


def test_mcp_pending_payments():
    # Setup a pending deal
    resellops_create_deal(
        product="Xbox Series X 1TB",
        seller_name="Markus",
        agreed_price_net=280.0,
        seller_paypal_email="markus@paypal.me"
    )
    pending_text = resellops_get_pending_payments()
    assert "Markus" in pending_text
    assert "Xbox Series X" in pending_text
    assert "markus@paypal.me" in pending_text


def test_mcp_update_and_payout():
    create_res = resellops_create_deal(
        product="MacBook Air M2 256GB Midnight",
        seller_name="Isa",
        agreed_price_net=550.0
    )
    # Extract created ID
    import re
    deal_id = int(re.search(r"Deal #(\d+)", create_res).group(1))

    # Update status to in transit
    up_res = resellops_update_deal_status(
        deal_id=deal_id,
        new_status="IN_TRANSIT_OR_WAREHOUSE",
        dhl_tracking="239080130725",
        rebuy_trn="TRN70328869"
    )
    assert "IN_TRANSIT_OR_WAREHOUSE" in up_res
    assert "239080130725" in up_res

    # Payout from Rebuy
    payout_res = resellops_record_rebuy_payout(
        deal_id=deal_id,
        selling_price=652.69
    )
    assert "Rebuy Auszahlung für Deal #" in payout_res
    assert "652.69 €" in payout_res
    assert "COMPLETED" in payout_res


def test_mcp_pipeline_summary():
    resellops_create_deal(
        product="Mac Mini M2 256GB",
        seller_name="Thomas",
        agreed_price_net=320.0
    )
    summary_text = resellops_get_pipeline_summary()
    assert "📊 ResellOps Pipeline Summary:" in summary_text
    assert "Gesamt-Deals:" in summary_text
