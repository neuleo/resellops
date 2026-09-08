"""ResellOps FastAPI Application Backend.

Provides RESTful endpoints for deal management, pipeline summaries,
status transitions, Rebuy payouts, and WebSocket live-reload for the Kanban dashboard.
"""

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.database import (
    init_db,
    create_deal,
    get_deal,
    update_deal,
    delete_deal,
    list_deals,
    get_pipeline_summary,
    get_pending_payments,
)
from core.models import (
    Deal,
    DealCreate,
    DealUpdate,
    DealStatus,
    PipelineSummary,
)
from core.calculator import calculate_margin_and_vat, calculate_paypal_gross
from app.schemas import StatusUpdateRequest, PayoutRequest, DeleteResponse
from app.websocket import ws_manager

STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend"
if not STATIC_DIR.exists():
    STATIC_DIR = Path("/app/frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initializes database on startup."""
    init_db()
    yield


app = FastAPI(
    title="ResellOps Command-Center API",
    description="Arbitrage Deal Pipeline, § 25a UStG Calculator & 1-Click PayPal Kanban API",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and container networking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Health & Status Definitions
# ---------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestrators and monitoring."""
    return {"status": "ok", "service": "ResellOps API", "version": "1.0.0"}


@app.get("/api/statuses", tags=["Metadata"])
async def list_statuses():
    """Returns available deal statuses with display metadata."""
    return [
        {
            "key": DealStatus.NEGOTIATING.value,
            "label": "Verhandlung",
            "description": "Angebot abgegeben / In Verhandlung",
            "color": "amber",
        },
        {
            "key": DealStatus.PAYPAL_PENDING.value,
            "label": "PayPal ausstehend",
            "description": "Zuschlag erhalten, Käuferschutz-Zahlung fällig",
            "color": "blue",
        },
        {
            "key": DealStatus.PAID_WAITING_SHIPPING.value,
            "label": "Bezahlt (Warte auf Versand)",
            "description": "Geld transferiert, Warte auf DHL Sendungsnummer",
            "color": "indigo",
        },
        {
            "key": DealStatus.IN_TRANSIT_OR_WAREHOUSE.value,
            "label": "Im Transit / Rebuy",
            "description": "Paket unterwegs oder bei Rebuy im Wareneingang",
            "color": "purple",
        },
        {
            "key": DealStatus.COMPLETED.value,
            "label": "Abgeschlossen",
            "description": "Rebuy Auszahlung verbucht & Marge realisiert",
            "color": "emerald",
        },
        {
            "key": DealStatus.CANCELLED.value,
            "label": "Storniert / Erstattet",
            "description": "Kauf abgebrochen oder Fall über Käuferschutz",
            "color": "rose",
        },
    ]


# ---------------------------------------------------------
# Deals Endpoints
# ---------------------------------------------------------

@app.get("/api/deals", response_model=List[Deal], tags=["Deals"])
async def get_deals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by DealStatus key"),
    search: Optional[str] = Query(None, description="Search term across product, seller, TRN, tracking"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieves all deals, optionally filtered by status and keyword search."""
    stat_enum = None
    if status_filter:
        try:
            stat_enum = DealStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{status_filter}'. Valid options: {[s.value for s in DealStatus]}",
            )
    return list_deals(status=stat_enum, search=search, limit=limit, offset=offset)


@app.post("/api/deals", response_model=Deal, status_code=status.HTTP_201_CREATED, tags=["Deals"])
async def create_new_deal(deal_input: DealCreate):
    """Creates a new deal, auto-computes PayPal gross amount, and notifies live clients."""
    data = deal_input.model_dump()
    if data.get("purchase_price_net") and not data.get("paypal_gross_amount"):
        data["paypal_gross_amount"] = calculate_paypal_gross(data["purchase_price_net"])

    if data.get("purchase_price_net") and (data.get("status") == DealStatus.NEGOTIATING or data.get("status") == DealStatus.NEGOTIATING.value):
        data["status"] = DealStatus.PAYPAL_PENDING.value

    updated_input = DealCreate(**data)
    created = create_deal(updated_input)
    await ws_manager.broadcast({
        "event": "deal_created",
        "deal_id": created.id,
        "product": created.product,
        "status": created.status,
    })
    return created


@app.get("/api/deals/{deal_id}", response_model=Deal, tags=["Deals"])
async def get_single_deal(deal_id: int):
    """Fetches details for a single deal by ID."""
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal #{deal_id} not found")
    return deal


@app.patch("/api/deals/{deal_id}", response_model=Deal, tags=["Deals"])
async def update_existing_deal(deal_id: int, updates: DealUpdate):
    """Updates fields on an existing deal and recalculates financials."""
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal #{deal_id} not found")

    updated = update_deal(deal_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal #{deal_id} not found")

    await ws_manager.broadcast({
        "event": "deal_updated",
        "deal_id": updated.id,
        "product": updated.product,
        "status": updated.status,
    })
    return updated


@app.delete("/api/deals/{deal_id}", response_model=DeleteResponse, tags=["Deals"])
async def remove_deal(deal_id: int):
    """Deletes a deal from the pipeline."""
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal #{deal_id} not found")

    deleted = delete_deal(deal_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete deal")

    await ws_manager.broadcast({
        "event": "deal_deleted",
        "deal_id": deal_id,
    })
    return DeleteResponse(
        success=True,
        message=f"Deal #{deal_id} ({deal.product}) was deleted.",
        deal_id=deal_id,
    )


# ---------------------------------------------------------
# Quick Action Workflow Endpoints
# ---------------------------------------------------------

@app.post("/api/deals/{deal_id}/status", response_model=Deal, tags=["Workflow"])
async def update_deal_status(deal_id: int, payload: StatusUpdateRequest):
    """Quickly advances or updates the workflow status of a deal."""
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal #{deal_id} not found")

    updates = DealUpdate(
        status=payload.status,
        dhl_tracking=payload.dhl_tracking or deal.dhl_tracking,
        rebuy_trn=payload.rebuy_trn or deal.rebuy_trn,
        notes=payload.notes if payload.notes is not None else deal.notes,
    )
    updated = update_deal(deal_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update deal")

    await ws_manager.broadcast({
        "event": "deal_status_changed",
        "deal_id": updated.id,
        "new_status": updated.status,
    })
    return updated


@app.post("/api/deals/{deal_id}/payout", response_model=Deal, tags=["Workflow"])
async def record_payout(deal_id: int, payload: PayoutRequest):
    """Records Rebuy payout, calculates differential tax (§ 25a UStG), and marks as COMPLETED."""
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal #{deal_id} not found")

    vk_dec = payload.selling_price
    effective_ek = deal.paypal_gross_amount if deal.paypal_gross_amount is not None else (deal.purchase_price_net or Decimal("0.00"))
    margin_res = calculate_margin_and_vat(effective_ek, vk_dec)

    updates = DealUpdate(
        status=DealStatus.COMPLETED,
        selling_price=vk_dec,
        gross_margin=margin_res.gross_margin,
        vat_25a=margin_res.vat_25a,
        net_profit=margin_res.net_profit,
    )
    updated = update_deal(deal_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record payout")

    await ws_manager.broadcast({
        "event": "deal_payout_recorded",
        "deal_id": updated.id,
        "selling_price": float(updated.selling_price or 0),
        "net_profit": float(updated.net_profit or 0),
    })
    return updated


# ---------------------------------------------------------
# Analytics & Aggregates
# ---------------------------------------------------------

@app.get("/api/summary", response_model=PipelineSummary, tags=["Analytics"])
async def get_summary():
    """Returns high-level business analytics, active capital, margins, and taxes."""
    return get_pipeline_summary()


@app.get("/api/pending", response_model=List[Deal], tags=["Analytics"])
async def get_pending():
    """Returns deals waiting for 1-Click PayPal payment."""
    return get_pending_payments()


# ---------------------------------------------------------
# Real-Time WebSocket Endpoint
# ---------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint providing real-time live reload signals to dashboards."""
    await ws_manager.connect(websocket)
    try:
        # Send initial connected message
        await websocket.send_json({"event": "connected", "message": "Connected to ResellOps Live Stream"})
        while True:
            # Keep connection alive, listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
@app.get("/index.htm", include_in_schema=False)
async def serve_dashboard():
    """Serves the single-page Kanban dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "ResellOps API running. Dashboard index.html not found."})


# ---------------------------------------------------------
# Frontend Static Files Mount
# ---------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
