"""Domain models and data contracts for ResellOps."""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.calculator import (
    calculate_paypal_gross,
    calculate_margin_and_vat,
    _round_currency,
    _to_decimal,
)


class DealStatus(str, Enum):
    """Lifecycle stages for a ResellOps arbitrage deal."""
    NEGOTIATING = "NEGOTIATING"
    PAYPAL_PENDING = "PAYPAL_PENDING"
    PAID_WAITING_SHIPPING = "PAID_WAITING_SHIPPING"
    IN_TRANSIT_OR_WAREHOUSE = "IN_TRANSIT_OR_WAREHOUSE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DealBase(BaseModel):
    """Base fields for a deal."""
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        validate_assignment=True,
    )

    product: str = Field(..., description="Device or item description (e.g. MacBook Air 13 M2 8GB 256GB)")
    seller_name: str = Field(..., description="Name or handle of Kleinanzeigen seller")
    status: DealStatus = Field(default=DealStatus.NEGOTIATING, description="Current workflow status")
    buy_date: Optional[date] = Field(default=None, description="Date purchase was agreed or paid")
    sell_date: Optional[date] = Field(default=None, description="Date item was sold/credited by Rebuy")
    purchase_price_net: Optional[Decimal] = Field(default=None, description="Agreed net purchase price for seller")
    paypal_gross_amount: Optional[Decimal] = Field(default=None, description="Gross PayPal payment including Käuferschutz fee")
    selling_price: Optional[Decimal] = Field(default=None, description="Actual or expected selling price from Rebuy")
    gross_margin: Optional[Decimal] = Field(default=None, description="Gross profit (VK - effective EK)")
    vat_25a: Optional[Decimal] = Field(default=None, description="§ 25a UStG differential tax on positive margin")
    net_profit: Optional[Decimal] = Field(default=None, description="Net profit after § 25a differential tax")
    rebuy_trn: Optional[str] = Field(default=None, description="Rebuy transaction or order reference (TRN...)")
    dhl_tracking: Optional[str] = Field(default=None, description="DHL shipping tracking number")
    serial_number: Optional[str] = Field(default=None, description="Device serial number (Apple SN)")
    order_number: Optional[str] = Field(default=None, description="Internal or marketplace order reference")
    notes: Optional[str] = Field(default=None, description="Additional context or handover notes")


class DealCreate(DealBase):
    """Payload for creating a new deal, with automated financial calculations."""

    @model_validator(mode="after")
    def compute_financials(self) -> "DealCreate":
        # 1. Calculate PayPal Gross if Net is provided and Gross is missing
        if self.purchase_price_net is not None and self.paypal_gross_amount is None:
            self.paypal_gross_amount = calculate_paypal_gross(self.purchase_price_net)

        # 2. Determine effective purchase cost
        effective_cost = self.paypal_gross_amount if self.paypal_gross_amount is not None else self.purchase_price_net

        # 3. If selling price is provided and effective cost is known, calculate margin & VAT
        if self.selling_price is not None and effective_cost is not None:
            # Special handling for cancelled / refunded deals where margin is forced to 0
            if self.status == DealStatus.CANCELLED:
                if self.gross_margin is None:
                    self.gross_margin = Decimal("0.00")
                if self.vat_25a is None:
                    self.vat_25a = Decimal("0.00")
                if self.net_profit is None:
                    self.net_profit = Decimal("0.00")
            else:
                margin_res = calculate_margin_and_vat(effective_cost, self.selling_price)
                if self.gross_margin is None:
                    self.gross_margin = margin_res.gross_margin
                if self.vat_25a is None:
                    self.vat_25a = margin_res.vat_25a
                if self.net_profit is None:
                    self.net_profit = margin_res.net_profit

        return self


class DealUpdate(BaseModel):
    """Payload for updating an existing deal."""
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        validate_assignment=True,
    )

    product: Optional[str] = None
    seller_name: Optional[str] = None
    status: Optional[DealStatus] = None
    buy_date: Optional[date] = None
    sell_date: Optional[date] = None
    purchase_price_net: Optional[Decimal] = None
    paypal_gross_amount: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    vat_25a: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    rebuy_trn: Optional[str] = None
    dhl_tracking: Optional[str] = None
    serial_number: Optional[str] = None
    order_number: Optional[str] = None
    notes: Optional[str] = None


class Deal(DealBase):
    """Persisted Deal entity with database identifiers and timestamps."""
    id: int = Field(..., description="Unique database ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")


class PipelineSummary(BaseModel):
    """High-level summary of active pipeline and financial totals."""
    total_deals: int = Field(default=0, description="Total number of all tracked deals")
    active_deals: int = Field(default=0, description="Deals currently in progress (not completed/cancelled)")
    completed_deals: int = Field(default=0, description="Completed deals")
    cancelled_deals: int = Field(default=0, description="Cancelled / refunded deals")
    status_counts: Dict[str, int] = Field(default_factory=dict, description="Count per DealStatus")
    total_spent: Decimal = Field(default=Decimal("0.00"), description="Total purchase capital deployed")
    total_revenue: Decimal = Field(default=Decimal("0.00"), description="Total revenue generated from sales")
    total_gross_margin: Decimal = Field(default=Decimal("0.00"), description="Cumulative gross profit")
    total_vat_25a: Decimal = Field(default=Decimal("0.00"), description="Cumulative § 25a UStG differential tax")
    total_net_profit: Decimal = Field(default=Decimal("0.00"), description="Cumulative net profit")
