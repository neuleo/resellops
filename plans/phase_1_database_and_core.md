# Phase 1: Core Database, Domain Models & Seed Data

## 🎯 Ziel
Ein robustes, eigenständiges Python-Datenbank- und Logikmodul im Ordner `/mnt/docker/resellops/core/` aufbauen, das alle Deals speichert, Berechnungen ausführt und die 14 bisherigen Rebuy-Deals von Leon importiert.

## 📦 Anforderungen an den Subagenten

1. **Dateistruktur:**
   ```text
   /mnt/docker/resellops/
   ├── core/
   │   ├── __init__.py
   │   ├── database.py       # SQLite Connection, WAL-Mode, Init-Tables
   │   ├── models.py         # Dataclasses / Pydantic Models für Deals
   │   ├── calculator.py     # PayPal-Gebührenformel & § 25a UStG Formel
   │   └── seed_data.py      # Import-Script für die 14 bestehenden Deals
   ├── tests/
   │   ├── __init__.py
   │   └── test_calculator.py# Unit-Tests für PayPal- und USt-Berechnungen
   ```

2. **Genaue Berechnungslogik (`calculator.py`):**
   * **PayPal-Käuferschutz:** Um bei Verkäufer $N$ anzukommen, muss Leon $B$ zahlen:
     $$B = \frac{N + 0,35}{1 - 0,0249}$$ (auf 2 Dezimalstellen kaufmännisch gerundet).
   * **Differenzbesteuerung § 25a UStG:**
     * Bruttomarge = $VK - EK$
     * Wenn Bruttomarge > 0: $USt = \frac{\text{Bruttomarge}}{1,19} \times 0,19$
     * Reingewinn vor ESt = $\text{Bruttomarge} - USt$
     * Wenn Bruttomarge <= 0: $USt = 0$, Reingewinn = $\text{Bruttomarge}$

3. **Status-Enums:**
   * `NEGOTIATING` (Verhandlung läuft)
   * `PAYPAL_PENDING` (Zuschlag da, PayPal-Adresse erhalten, wartet auf Zahlung)
   * `PAID_WAITING_SHIPPING` (Bezahlt, Verkäufer muss versenden)
   * `IN_TRANSIT_OR_WAREHOUSE` (Unterwegs zu Rebuy / Zwischenlager)
   * `COMPLETED` (Rebuy hat geprüft & ausgezahlt)
   * `CANCELLED` (Storniert / erstattet mit 0 € Marge)

4. **14 Historische Deals importieren (`seed_data.py`):**
   * Andrew, S.E, Max Pfeufer, Jan Groll, Isa, Finn, Daniel, Brandon, Elias, Rene Patricio, Thomas Mosch, Hannah, Robin, CCl mit allen bekannten Feldern (EK, VK, Marge, TRN, Sendungsnummern).

5. **Verifikation:**
   * Pytest oder unittests müssen erfolgreich durchlaufen.
