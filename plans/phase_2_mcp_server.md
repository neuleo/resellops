# Phase 2: ResellOps MCP-Server für Cronjob-Automatisierung

## 🎯 Ziel
Einen leichtgewichtigen Python MCP-Server unter `/mnt/docker/resellops/mcp/` implementieren, der über Stdio läuft. Er erlaubt den Kleinanzeigen- und Rebuy-Cronjobs, Deals direkt in der ResellOps-Datenbank anzulegen und den Status zu wechseln.

## 🛠️ Bereitzustellende MCP-Tools

1. `resellops_create_deal(product_name, seller_name, listing_url, agreed_price_net, seller_paypal_email, campaign_name)`
   * Berechnet automatisch den benötigten PayPal-Bruttobetrag.
   * Setzt Status standardmäßig auf `PAYPAL_PENDING`.
   * Gibt formatierte Deal-Zusammenfassung zurück.

2. `resellops_update_deal_status(deal_id, new_status, optional_dhl_tracking, optional_rebuy_trn)`
   * Aktualisiert den Status in der SQLite-Datenbank.

3. `resellops_record_rebuy_payout(deal_id, selling_price)`
   * Berechnet finale Bruttomarge, § 25a USt und Reingewinn.
   * Setzt Status auf `COMPLETED`.

4. `resellops_get_pending_payments()`
   * Liefert alle Deals zurück, die auf Leons 1-Click PayPal-Zahlung warten (inkl. vorberechnetem Betrag).

5. `resellops_get_pipeline_summary()`
   * Liefert KPIs: Offene Deals, gebundenes Kapital, erwarteter Gewinn, realisierter Gewinn.
