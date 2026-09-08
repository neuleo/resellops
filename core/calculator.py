"""Calculation engine for ResellOps.

Implements:
1. PayPal Käuferschutz fee calculation:
   Gross payment needed so seller receives agreed net amount:
   B = (N + 0.35) / (1 - 0.0249)

2. Differenzbesteuerung § 25a UStG:
   Gross margin = VK - EK
   If Gross margin > 0:
       USt = (Gross margin / 1.19) * 0.19
       Net profit = Gross margin - USt
   If Gross margin <= 0:
       USt = 0
       Net profit = Gross margin
"""

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Union

NumberLike = Union[Decimal, float, int, str]

# PayPal Fee constants for Germany
PAYPAL_FIXED_FEE = Decimal("0.35")
PAYPAL_VARIABLE_RATE = Decimal("0.0249")
PAYPAL_NET_FACTOR = Decimal("1") - PAYPAL_VARIABLE_RATE  # 0.9751

# Tax constants (§ 25a UStG)
VAT_RATE_25A = Decimal("0.19")
VAT_DIVISOR_25A = Decimal("1.19")

CENT = Decimal("0.01")


def _to_decimal(val: NumberLike) -> Decimal:
    """Safely converts a number-like value to Decimal with proper precision."""
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _round_currency(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using standard commercial rounding (ROUND_HALF_UP)."""
    return val.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_paypal_gross(net_amount: NumberLike) -> Decimal:
    """Calculates the gross PayPal payment amount required so the seller receives `net_amount`.

    Formula:
        B = (N + 0.35) / (1 - 0.0249)

    Args:
        net_amount: The target net amount the seller should receive.

    Returns:
        The gross payment amount rounded to 2 decimal places (EUR).
    """
    n = _to_decimal(net_amount)
    if n < Decimal("0"):
        raise ValueError("Net amount must be non-negative")
    if n == Decimal("0"):
        return _round_currency(PAYPAL_FIXED_FEE / PAYPAL_NET_FACTOR)

    gross = (n + PAYPAL_FIXED_FEE) / PAYPAL_NET_FACTOR
    return _round_currency(gross)


def calculate_paypal_fee(gross_amount: NumberLike) -> Decimal:
    """Calculates the standard PayPal merchant/buyer protection fee deducted from gross amount.

    Formula:
        fee = round(gross * 0.0249 + 0.35, 2)
    """
    g = _to_decimal(gross_amount)
    if g < Decimal("0"):
        raise ValueError("Gross amount must be non-negative")
    fee = (g * PAYPAL_VARIABLE_RATE) + PAYPAL_FIXED_FEE
    return _round_currency(fee)


def calculate_paypal_net(gross_amount: NumberLike) -> Decimal:
    """Calculates the net amount a seller receives after PayPal fee deduction.

    Formula:
        net = gross - fee
    """
    g = _to_decimal(gross_amount)
    fee = calculate_paypal_fee(g)
    return g - fee


@dataclass(frozen=True)
class MarginResult:
    """Result of § 25a UStG margin taxation calculation."""
    purchase_price: Decimal
    selling_price: Decimal
    gross_margin: Decimal
    vat_25a: Decimal
    net_profit: Decimal

    @property
    def roi_percent(self) -> Decimal:
        """Return ROI percentage relative to purchase price."""
        if self.purchase_price > Decimal("0"):
            return _round_currency((self.gross_margin / self.purchase_price) * Decimal("100"))
        return Decimal("0.00")

    def to_dict(self) -> dict:
        return {
            "purchase_price": float(self.purchase_price),
            "selling_price": float(self.selling_price),
            "gross_margin": float(self.gross_margin),
            "vat_25a": float(self.vat_25a),
            "net_profit": float(self.net_profit),
            "roi_percent": float(self.roi_percent),
        }


def calculate_margin_and_vat(
    purchase_price: NumberLike,
    selling_price: NumberLike,
) -> MarginResult:
    """Calculates gross margin, § 25a UStG differential VAT, and net profit.

    Rules:
    - Gross margin = selling_price - purchase_price
    - If gross margin > 0:
        USt = round((gross margin / 1.19) * 0.19, 2)
        Net profit = gross margin - USt
    - If gross margin <= 0:
        USt = 0.00
        Net profit = gross margin

    Args:
        purchase_price: Total purchase cost (EK).
        selling_price: Total sale revenue (VK).

    Returns:
        MarginResult dataclass.
    """
    ek = _round_currency(_to_decimal(purchase_price))
    vk = _round_currency(_to_decimal(selling_price))

    gross_margin = vk - ek

    if gross_margin > Decimal("0"):
        vat = _round_currency((gross_margin / VAT_DIVISOR_25A) * VAT_RATE_25A)
        net_profit = gross_margin - vat
    else:
        vat = Decimal("0.00")
        net_profit = gross_margin

    return MarginResult(
        purchase_price=ek,
        selling_price=vk,
        gross_margin=gross_margin,
        vat_25a=vat,
        net_profit=net_profit,
    )
