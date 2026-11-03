# EcoReceipt — Python Web Prototype

A Flask + SQLite prototype based on the EcoReceipt Chapter I–II document for Mavailine Marketing.

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run `python -m venv .venv`
4. Activate it:
   - Windows: `.venv\\Scripts\\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. Run `pip install -r requirements.txt`
6. Run `python app.py`
7. Open `http://127.0.0.1:5000`

## Demo accounts
- Admin: `admin` / `admin123`
- Cashier: `cashier` / `cashier123`
- Warehouse: `warehouse` / `warehouse123`

## Included
- Role-based demo login
- Dashboard and KPIs
- Product and stock management
- Order entry with automatic totals and stock validation
- Receipt generation and print-friendly receipt page
- Delivery checklist and fulfillment status
- Admin sales summary reports
- SQLite local database

## Important prototype limitations
This is a local demonstration, not a production cloud deployment. It uses SQLite and demo plaintext passwords for easy classroom testing. Before real deployment, add password hashing, CSRF protection, audit logging, secure secrets, database migrations/backups, HTTPS, and a hosted database. It does not integrate SMS ingestion, live multi-device cloud sync, or a physical thermal printer; receipt printing uses the browser print dialog.
