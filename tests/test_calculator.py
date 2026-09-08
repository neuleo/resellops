"""Unit tests for ResellOps calculation engine (core.calculator)."""

from decimal import Decimal
import pytest

from core.calculator import (
    calculate_paypal_gross,
    calculate_paypal_fee,
    calculate_paypal_net,
    calculate_margin_and_vat,
    MarginResult,
)


@pytest.mark.parametrize(
    "net_input, expected_gross",
    [
        (Decimal("370.00"), Decimal("379.81")),
        (Decimal("400.00"), Decimal("410.57")),
        (Decimal("420.00"), Decimal("431.08")),
        (Decimal("500.00"), Decimal("513.13")),
        (Decimal("550.00"), Decimal("564.40")),
        (Decimal("580.00"), Decimal("595.17")),
        (Decimal("585.00"), Decimal("600.30")),
        (370, Decimal("379.81")),
        ("400", Decimal("410.57")),
        (550.0, Decimal("564.40")),
    ],
)
def test_calculate_paypal_gross_benchmark_values(net_input, expected_gross):
    """Verifies official PayPal buyer protection gross formula against benchmark table."""
    result = calculate_paypal_gross(net_input)
    assert result == expected_gross


def test_calculate_paypal_gross_zero():
    """Zero net amount requires gross paying the minimum fixed fee."""
    result = calculate_paypal_gross(0)
    assert result == Decimal("0.36")


def test_calculate_paypal_gross_negative_raises():
    """Negative amounts must raise ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        calculate_paypal_gross(-10)


def test_paypal_fee_and_net_consistency():
    """Verifies that subtracting fee from gross yields exactly the target net amount (within 0.01 €)."""
    agreed_net = Decimal("550.00")
    gross = calculate_paypal_gross(agreed_net)  # 564.40
    fee = calculate_paypal_fee(gross)          # round(564.40 * 0.0249 + 0.35, 2) = 14.40
    net_received = calculate_paypal_net(gross)  # 564.40 - 14.40 = 550.00

    assert gross == Decimal("564.40")
    assert fee == Decimal("14.40")
    assert net_received == agreed_net


@pytest.mark.parametrize(
    "ek, vk, exp_gross_margin, exp_vat, exp_net_profit",
    [
        # Andrew: EK 410.57, VK 538.34 -> 127.77 margin
        (Decimal("410.57"), Decimal("538.34"), Decimal("127.77"), Decimal("20.40"), Decimal("107.37")),
        # S.E: EK 492.62, VK 561.56 -> 68.94 margin
        (Decimal("492.62"), Decimal("561.56"), Decimal("68.94"), Decimal("11.01"), Decimal("57.93")),
        # Elias: EK 595.17, VK 696.79 -> 101.62 margin, VAT = 16.23, Net = 85.39
        (Decimal("595.17"), Decimal("696.79"), Decimal("101.62"), Decimal("16.23"), Decimal("85.39")),
    ],
)
def test_differential_tax_positive_margin(ek, vk, exp_gross_margin, exp_vat, exp_net_profit):
    """Checks § 25a UStG differential tax calculation on profitable deals."""
    res = calculate_margin_and_vat(ek, vk)
    assert res.purchase_price == ek
    assert res.selling_price == vk
    assert res.gross_margin == exp_gross_margin
    assert res.vat_25a == exp_vat
    assert res.net_profit == exp_net_profit


def test_differential_tax_zero_margin():
    """Refunds/break-even deals incur 0.00 € VAT and 0.00 € net profit."""
    res = calculate_margin_and_vat(Decimal("433.96"), Decimal("433.96"))
    assert res.gross_margin == Decimal("0.00")
    assert res.vat_25a == Decimal("0.00")
    assert res.net_profit == Decimal("0.00")


def test_differential_tax_negative_margin():
    """Loss deals incur 0.00 € VAT; net profit equals negative gross margin."""
    res = calculate_margin_and_vat(Decimal("500.00"), Decimal("450.00"))
    assert res.gross_margin == Decimal("-50.00")
    assert res.vat_25a == Decimal("0.00")
    assert res.net_profit == Decimal("-50.00")


def test_margin_result_properties():
    """Tests ROI calculation and dictionary export."""
    res = calculate_margin_and_vat(Decimal("400.00"), Decimal("500.00"))
    assert res.roi_percent == Decimal("25.00")
    
    d = res.to_dict()
    assert d["purchase_price"] == 400.0
    assert d["selling_price"] == 500.0
    assert d["gross_margin"] == 100.0
    assert d["vat_25a"] == 15.97
    assert d["net_profit"] == 84.03
    assert d["roi_percent"] == 25.0
