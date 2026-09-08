"""
ResellOps FastMCP Server
Exposes deal management and pipeline tracking tools for Hermes Agent and Cronjobs.
"""

from decimal import Decimal
from typing import Optional
from mcp.server.fastmcp import FastMCP

from core.database import (
    create_deal,
    get_deal,
    update_deal,
    get_pending_payments,
    get_pipeline_summary,
    init_db
)
from core.models import DealCreate, DealUpdate, DealStatus
from core.calculator import calculate_paypal_gross, calculate_margin_and_vat

# Initialize FastMCP application
mcp = FastMCP("resellops-mcp")

def _status_val(status) -> str:
    return status.value if hasattr(status, "value") else str(status)

# Ensure DB schema is up to date on server start
init_db()


@mcp.tool()
def resellops_create_deal(
    product: str,
    seller_name: str,
    listing_url: str = "",
    agreed_price_net: float = 0.0,
    seller_paypal_email: str = "",
    campaign_name: str = "",
    notes: str = ""
) -> str:
    """
    Creates a new deal in the ResellOps pipeline.
    Calculates exact PayPal gross payment amount and sets status to PAYPAL_PENDING.
    """
    net_dec = Decimal(str(agreed_price_net))
    gross_dec = calculate_paypal_gross(net_dec) if net_dec > 0 else Decimal("0.00")
    status = DealStatus.PAYPAL_PENDING if net_dec > 0 else DealStatus.NEGOTIATING

    deal_create = DealCreate(
        product=product,
        seller_name=seller_name,
        status=status,
        purchase_price_net=net_dec,
        paypal_gross_amount=gross_dec,
        listing_url=listing_url or None,
        seller_paypal_email=seller_paypal_email or None,
        campaign_name=campaign_name or None,
        notes=notes or None
    )

    created = create_deal(deal_create)
    return (
        f"✅ Deal #{created.id} erfolgreich angelegt!\n"
        f"• Produkt: {created.product}\n"
        f"• Verkäufer: {created.seller_name} ({created.seller_paypal_email or 'Keine PayPal-Mail'})\n"
        f"• Verhandelter Netto-Preis: {created.purchase_price_net:.2f} €\n"
        f"• Zu zahlender PayPal-Bruttobetrag (Käuferschutz): {created.paypal_gross_amount:.2f} €\n"
        f"• Status: {_status_val(created.status)}"
    )


@mcp.tool()
def resellops_update_deal_status(
    deal_id: int,
    new_status: str,
    dhl_tracking: str = "",
    rebuy_trn: str = "",
    notes: str = ""
) -> str:
    """
    Updates status and tracking info for an existing deal.
    Allowed statuses: NEGOTIATING, PAYPAL_PENDING, PAID_WAITING_SHIPPING,
    IN_TRANSIT_OR_WAREHOUSE, COMPLETED, CANCELLED.
    """
    try:
        status_enum = DealStatus(new_status)
    except ValueError:
        return f"❌ Ungültiger Status '{new_status}'. Erlaubt sind: {[s.value for s in DealStatus]}"

    update_payload = DealUpdate(
        status=status_enum,
        dhl_tracking=dhl_tracking or None,
        rebuy_trn=rebuy_trn or None,
        notes=notes or None
    )

    updated = update_deal(deal_id, update_payload)
    if not updated:
        return f"❌ Deal #{deal_id} nicht gefunden."

    return (
        f"✅ Deal #{updated.id} aktualisiert!\n"
        f"• Neuer Status: {_status_val(updated.status)}\n"
        f"• DHL Tracking: {updated.dhl_tracking or '-'}\n"
        f"• Rebuy TRN: {updated.rebuy_trn or '-'}"
    )


@mcp.tool()
def resellops_record_rebuy_payout(
    deal_id: int,
    selling_price: float
) -> str:
    """
    Records Rebuy final payout for a deal.
    Calculates gross margin, § 25a UStG differential VAT, and net profit.
    Marks deal as COMPLETED.
    """
    deal = get_deal(deal_id)
    if not deal:
        return f"❌ Deal #{deal_id} nicht gefunden."

    vk_dec = Decimal(str(selling_price))
    ek_dec = deal.purchase_price_net or Decimal("0.00")
    margin_res = calculate_margin_and_vat(ek_dec, vk_dec)

    update_payload = DealUpdate(
        status=DealStatus.COMPLETED,
        selling_price=vk_dec,
        gross_margin=margin_res.gross_margin,
        vat_25a=margin_res.vat_25a,
        net_profit=margin_res.net_profit
    )

    updated = update_deal(deal_id, update_payload)
    if not updated:
        return f"❌ Fehler beim Aktualisieren von Deal #{deal_id}."
    return (
        f"🎉 Rebuy Auszahlung für Deal #{updated.id} verbucht!\n"
        f"• Produkt: {updated.product} ({updated.seller_name})\n"
        f"• Verkaufserlös: {updated.selling_price:.2f} € (EK: {updated.purchase_price_net:.2f} €)\n"
        f"• Brutto-Marge: {updated.gross_margin:.2f} €\n"
        f"• USt 19 % (§ 25a): {updated.vat_25a:.2f} €\n"
        f"• Reingewinn vor ESt: {updated.net_profit:.2f} €\n"
        f"• Status: {_status_val(updated.status)}"
    )


@mcp.tool()
def resellops_get_pending_payments() -> str:
    """
    Returns all deals waiting for PayPal payment with precalculated amounts.
    """
    pending = get_pending_payments()
    if not pending:
        return "ℹ️ Keine offenen Zahlungen. Alle Deals sind bezahlt oder in Verhandlung."

    lines = [f"📋 Offene PayPal-Zahlungen ({len(pending)} Deal(s)):"]
    for d in pending:
        lines.append(
            f"• [ID #{d.id}] {d.product}\n"
            f"  Verkäufer: {d.seller_name} | Mail: {d.seller_paypal_email or '⚠️ FEHLT'}\n"
            f"  Betrag (exakt brutto): {d.paypal_gross_amount:.2f} € (Netto vereinbart: {d.purchase_price_net:.2f} €)\n"
            f"  Link: {d.listing_url or '-'}"
        )
    return "\n".join(lines)


@mcp.tool()
def resellops_get_pipeline_summary() -> str:
    """
    Returns comprehensive KPIs and pipeline overview of all deals.
    """
    summary = get_pipeline_summary()
    return (
        f"📊 ResellOps Pipeline Summary:\n"
        f"• Gesamt-Deals: {summary.total_deals} (Aktiv: {summary.active_deals} | Abgeschlossen: {summary.completed_deals} | Storniert: {summary.cancelled_deals})\n"
        f"• Gebundenes Kapital (laufend): {summary.active_capital_tied:.2f} €\n"
        f"• Gesamtumsatz (Rebuy-Erlöse): {summary.total_revenue:.2f} €\n"
        f"• Gesamter Bruttogewinn: {summary.total_gross_margin:.2f} €\n"
        f"• Kumulierte USt (§ 25a): {summary.total_vat_25a:.2f} €\n"
        f"• Realisierter Reingewinn: {summary.realized_net_profit:.2f} €"
    )


if __name__ == "__main__":
    mcp.run()
