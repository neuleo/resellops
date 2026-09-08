"""
API Integration Tests for ResellOps FastAPI Backend.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.database import init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provides an isolated test client with a fresh temporary SQLite DB."""
    test_db = tmp_path / "test_api.db"
    init_db(test_db)
    monkeypatch.setattr("core.database.DEFAULT_DB_PATH", test_db)
    return TestClient(app)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ok", "healthy"]
    assert "ResellOps API" in data["service"]


def test_create_and_get_deal(client):
    # Create deal via API
    payload = {
        "product": "MacBook Air M1 256GB Space Grau",
        "seller_name": "Peter",
        "listing_url": "https://kleinanzeigen.de/s-anzeige/123",
        "purchase_price_net": 270.0,
        "seller_paypal_email": "peter@example.com",
        "campaign_name": "macbook_air_m1",
        "notes": "Top Zustand"
    }
    create_res = client.post("/api/deals", json=payload)
    assert create_res.status_code == 201
    deal = create_res.json()
    assert deal["id"] is not None
    assert deal["product"] == payload["product"]
    assert float(deal["paypal_gross_amount"]) == 277.25
    assert deal["status"] == "PAYPAL_PENDING"

    # Fetch all deals
    get_res = client.get("/api/deals")
    assert get_res.status_code == 200
    deals = get_res.json()
    assert len(deals) >= 1
    assert any(d["id"] == deal["id"] for d in deals)


def test_patch_status_and_payout(client):
    # Create deal
    create_res = client.post("/api/deals", json={
        "product": "MacBook Air M2 256GB Midnight",
        "seller_name": "Isa",
        "purchase_price_net": 550.0
    })
    deal_id = create_res.json()["id"]

    # Mark as Paid
    patch_res = client.patch(f"/api/deals/{deal_id}", json={
        "status": "PAID_WAITING_SHIPPING",
        "dhl_tracking": "239080130725"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "PAID_WAITING_SHIPPING"
    assert patch_res.json()["dhl_tracking"] == "239080130725"

    # Record payout
    payout_res = client.post(f"/api/deals/{deal_id}/payout", json={
        "selling_price": 652.69
    })
    assert payout_res.status_code == 200
    payout_data = payout_res.json()
    assert payout_data["status"] == "COMPLETED"
    # VK 652.69 - PayPal EK 564.40 = 88.29 gross margin
    assert float(payout_data["gross_margin"]) == 88.29
    assert float(payout_data["vat_25a"]) > 0
    assert float(payout_data["net_profit"]) > 0


def test_get_summary_kpis(client):
    res = client.get("/api/summary")
    assert res.status_code == 200
    summary = res.json()
    assert "total_deals" in summary
    assert "realized_net_profit" in summary
    assert "active_capital_tied" in summary
