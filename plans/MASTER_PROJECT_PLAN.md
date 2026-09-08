# ResellOps — Master-Projektplan & Feature-Tracking

> **Projektziel:** Ein maßgeschneidertes, vollautomatisiertes Command-Center für Arbitrage-Reselling (Kleinanzeigen ➔ Rebuy / Ankaufportale). Ersetzt manuelle Excel-Tabellen, automatisiert PayPal-Käuferschutz-Berechnungen, Rebuy-Auftragsanlage, DHL-Label-Versand und bietet einen dedizierten MCP-Server für Hermes-Cronjobs.

---

## 🏛️ Architektur & Prinzip („Orchestrator-Worker-Pattern“)
* **Orchestrator (Hermes Agent / Ich):** Strategische Planung, Prompt-Design für Tasks, Qualitätskontrolle, Verifikation von Tests, Release-Management. Schreibt selbst keinen Feature-Code.
* **Worker (Subagents via `delegate_task` mit Flash 3.8):** Autonome Implementierung der einzelnen Phasen in isolierten Terminal- und Code-Kontexten, Schreiben von Tests, Dokumentation und Commits.

---

## 🗺️ Phasen-Übersicht & Status

| Phase | Modul / Fokus | Status | Zieldatum / Meilenstein |
| :--- | :--- | :---: | :--- |
| **Phase 1** | **Core Database, Schema & Business-Logik** | ⏳ Bereit für Worker | SQLite, Migration existierender Deals, § 25a USt-Rechner, PayPal-Formel |
| **Phase 2** | **ResellOps MCP-Server** | ⏸️ Geplant | MCP-Tools für Hermes-Cronjobs (Deals erfassen, verschieben, abfragen) |
| **Phase 3** | **REST Backend API & Webhooks** | ⏸️ Geplant | FastAPI Endpoints, Statuswechsel, WebSocket für Live-Updates |
| **Phase 4** | **Frontend Kanban-Dashboard** | ⏸️ Geplant | Responsive Web-UI (Tailwind), 1-Click PayPal-Copy & Payment-Trigger |
| **Phase 5** | **Rebuy- & DHL-Automation Microservice** | ⏸️ Geplant | Headless Rebuy-Order-Erstellung, QR-Code Extractor & Chat-Injektor |
| **Phase 6** | **Docker Compose, GitHub CI & Invoice Ninja Sync** | ⏸️ Geplant | Multi-Container-Setup, Rechnungs-Export an Invoice Ninja API |

---

## 📋 Detaillierte Feature-Matrix & Akzeptanzkriterien

### 1. Datenmodell & Business-Engine (`plans/phase_1_database_and_core.md`)
- [ ] SQLite Schema mit strikten Types (Pragma foreign keys, WAL-Mode)
- [ ] Felder: `id`, `product`, `seller_name`, `status`, `buy_date`, `sell_date`, `purchase_price_net`, `paypal_gross_amount`, `selling_price`, `gross_margin`, `vat_25a`, `net_profit`, `rebuy_trn`, `dhl_tracking`, `serial_number`, `order_number`
- [ ] Mathematisch exakte PayPal-Käuferschutz-Formel: $G = \frac{\text{Netto} + 0,35}{1 - 0,0249}$
- [ ] § 25a UStG Differenzbesteuerungs-Rechner ($USt = \frac{\text{Marge}}{1,19} \times 0,19$)
- [ ] Import-Skript für die 14 bestehenden Deals aus dem Chat/Excel

### 2. ResellOps MCP-Server (`plans/phase_2_mcp_server.md`)
- [ ] Stdio-basierter MCP-Server (`resellops-mcp`)
- [ ] Tool: `resellops_create_deal` (aus Kleinanzeigen-Zuschlag)
- [ ] Tool: `resellops_update_deal_status` (Verhandlung ➔ PayPal bereit ➔ Bezahlt ➔ Im Transit ➔ Abgeschlossen)
- [ ] Tool: `resellops_get_active_pipeline`
- [ ] Tool: `resellops_calculate_paypal_amount`

### 3. Frontend Web-App (`plans/phase_4_frontend_dashboard.md`)
- [ ] Schnelles, reaktives UI (Kanban-Spalten)
- [ ] Karte mit allen Kennzahlen (EK, VK, Marge, Rebuy-Link)
- [ ] 1-Click Button `[PayPal öffnen & kopieren]`: Kopiert vorberechneten Betrag + Mail in Zwischenablage, öffnet PayPal Web-Maske
- [ ] Filter nach Status, Datum und Rentabilität

### 4. Integration & Deployment
- [ ] `docker-compose.yml` verbindet Backend, Dashboard und MCP
- [ ] Sauberes Git-Repository auf `neuleo/resellops`
- [ ] Dokumentation & Environment-Handling (`.env.example`)
