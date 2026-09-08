# Phase 3 & 4: REST Backend, Web-Dashboard & Docker Setup

## 🎯 Ziel
Ein modernes, ansprechendes Kanban-Web-Dashboard aufsetzen, das über `docker-compose.yml` gestartet wird und Leon die tägliche Arbeit auf 30 Sekunden verkürzt.

## 📦 Architektur
* **Backend:** FastAPI (`app/main.py`), bindet `core.database` an, bietet REST Endpoints (`/api/deals`, `/api/summary`) und WebSockets für Live-Reload.
* **Frontend:** Schlankes Single-Page-Dashboard (HTML5/TailwindCSS + Alpine.js oder React/Vite), läuft direkt über FastAPI Static Files oder Nginx.
* **Das Kernfeature (1-Click PayPal):**
  * Deal-Karte mit Button `[💳 PayPal Zahlung öffnen]`.
  * Kopiert den vorausberechneten Brutto-Betrag & E-Mail in das Clipboard.
  * Öffnet `https://www.paypal.com/myaccount/transfer/homepage/buy`.
  * Button `[Als bezahlt markieren]` schiebt die Karte mit 1 Klick in die nächste Spalte.
* **Deployment:**
  * `Dockerfile` für die Web-App + MCP
  * `docker-compose.yml` mit persistentem Volume für `/mnt/docker/resellops/data/resellops.db` auf Port `8088`.
