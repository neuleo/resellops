"""Pydantic schemas for API requests and responses."""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from core.models import DealStatus


class StatusUpdateRequest(BaseModel):
    """Payload to update the status and tracking info of a deal."""
    status: DealStatus
    dhl_tracking: Optional[str] = None
    rebuy_trn: Optional[str] = None
    notes: Optional[str] = None


class PayoutRequest(BaseModel):
    """Payload to record a Rebuy payout for a deal."""
    selling_price: Decimal = Field(..., gt=0, description="Final gross selling price received from Rebuy")


class DeleteResponse(BaseModel):
    """Response model for deal deletion."""
    success: bool
    message: str
    deal_id: int
