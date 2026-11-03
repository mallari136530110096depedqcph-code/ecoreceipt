import os 
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from pathlib import Path
from datetime import datetime
from functools import wraps

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ecoreceipt.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','cashier','warehouse')),
            display_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            store TEXT NOT NULL,
            delivery_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            subtotal REAL NOT NULL,
            discount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id),
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
            receipt_number TEXT NOT NULL UNIQUE,
            issued_at TEXT NOT NULL
        );
        """)
        count = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count == 0:
            # Demo-only accounts; replace passwords and add proper hashing before deployment.
            db.executemany(
                "INSERT INTO users(username,password,role,display_name) VALUES(?,?,?,?)",
                [
                    ("admin", "admin123", "admin", "Administrator"),
                    ("cashier", "cashier123", "cashier", "POS Cashier"),
                    ("warehouse", "warehouse123", "warehouse", "Warehouse Staff"),
                ],
            )
        pcount = db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        if pcount == 0:
            db.executemany(
                "INSERT INTO products(name,sku,unit_price,stock) VALUES(?,?,?,?)",
                [
                    ("Cooking Oil 1L", "OIL-001", 95.00, 120),
                    ("Rice 25kg", "RICE-025", 1250.00, 35),
                    ("Canned Goods Case", "CAN-024", 720.00, 50),
                    ("Laundry Detergent Case", "DET-012", 540.00, 42),
                    ("Bottled Water Case", "WAT-024", 180.00, 80),
                ],
            )

def login_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                flash("Your account does not have permission to open that page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_user():
    return {"current_user": session.get("display_name"), "current_role": session.get("role")}

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["display_name"] = user["display_name"]
            flash(f"Welcome back, {user['display_name']}.", "success")
            return redirect(url_for("dashboard"))
        flash("We couldn't match that username and password. Please try again.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required()
def dashboard():
    with get_db() as db:
        totals = {
            "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "pending": db.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'").fetchone()[0],
            "products": db.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
            "stock": db.execute("SELECT COALESCE(SUM(stock),0) FROM products WHERE active=1").fetchone()[0],
            "revenue": db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='Completed'").fetchone()[0],
        }
        recent = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 6").fetchall()
        low_stock = db.execute("SELECT * FROM products WHERE active=1 AND stock <= 10 ORDER BY stock ASC LIMIT 5").fetchall()
    return render_template("dashboard.html", totals=totals, recent=recent, low_stock=low_stock)

@app.route("/products", methods=["GET", "POST"])
@login_required("admin", "cashier")
def products():
    with get_db() as db:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            sku = request.form.get("sku", "").strip().upper()
            try:
                price = float(request.form.get("unit_price", ""))
                stock = int(request.form.get("stock", ""))
                if not name or not sku or price < 0 or stock < 0:
                    raise ValueError
                db.execute("INSERT INTO products(name,sku,unit_price,stock) VALUES(?,?,?,?)", (name, sku, price, stock))
                db.commit()
                flash("Product added to inventory.", "success")
                return redirect(url_for("products"))
            except ValueError:
                flash("Enter a product name, SKU, non-negative price, and whole-number stock.", "error")
            except sqlite3.IntegrityError:
                flash("That SKU already exists. Choose a unique SKU.", "error")
        q = request.args.get("q", "").strip()
        items = db.execute(
            "SELECT * FROM products WHERE active=1 AND (name LIKE ? OR sku LIKE ?) ORDER BY name",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    return render_template("products.html", products=items, query=q)

@app.route("/orders/new", methods=["GET", "POST"])
@login_required("admin", "cashier")
def new_order():
    with get_db() as db:
        inventory = db.execute("SELECT * FROM products WHERE active=1 AND stock>0 ORDER BY name").fetchall()
        if request.method == "POST":
            customer = request.form.get("customer", "").strip()
            store = request.form.get("store", "").strip()
            delivery_date = request.form.get("delivery_date", "").strip()
            discount_raw = request.form.get("discount", "0").strip()
            try:
                discount = float(discount_raw or 0)
                if not customer or not store or not delivery_date or discount < 0:
                    raise ValueError
                lines = []
                subtotal = 0.0
                for p in inventory:
                    raw_qty = request.form.get(f"qty_{p['id']}", "0").strip()
                    qty = int(raw_qty or 0)
                    if qty < 0:
                        raise ValueError
                    if qty:
                        if qty > p["stock"]:
                            raise ValueError(f"Not enough stock for {p['name']}. Available: {p['stock']}.")
                        line_total = round(qty * p["unit_price"], 2)
                        lines.append((p, qty, line_total))
                        subtotal += line_total
                if not lines:
                    raise ValueError("Add at least one product quantity before saving the order.")
                if discount > subtotal:
                    raise ValueError("Discount cannot be greater than the subtotal.")
                total = round(subtotal - discount, 2)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur = db.execute(
                    "INSERT INTO orders(customer,store,delivery_date,status,subtotal,discount,total,created_at) VALUES(?,?,?,'Pending',?,?,?,?)",
                    (customer, store, delivery_date, round(subtotal, 2), round(discount, 2), total, now)
                )
                order_id = cur.lastrowid
                for p, qty, line_total in lines:
                    db.execute(
                        "INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price,line_total) VALUES(?,?,?,?,?,?)",
                        (order_id, p["id"], p["name"], qty, p["unit_price"], line_total)
                    )
                    db.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty, p["id"]))
                receipt_no = f"ER-{datetime.now().strftime('%Y%m%d')}-{order_id:04d}"
                db.execute("INSERT INTO receipts(order_id,receipt_number,issued_at) VALUES(?,?,?)", (order_id, receipt_no, now))
                db.commit()
                flash("Order saved. Inventory was updated and a digital receipt was generated.", "success")
                return redirect(url_for("receipt", order_id=order_id))
            except ValueError as exc:
                flash(str(exc) or "Check the order details and quantities.", "error")
        return render_template("new_order.html", products=inventory, today=datetime.now().strftime("%Y-%m-%d"))

@app.route("/orders")
@login_required()
def orders():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sql = "SELECT * FROM orders WHERE (customer LIKE ? OR store LIKE ? OR CAST(id AS TEXT) LIKE ?)"
    args = [f"%{q}%", f"%{q}%", f"%{q}%"]
    if status in ("Pending", "Preparing", "Completed"):
        sql += " AND status=?"
        args.append(status)
    sql += " ORDER BY id DESC"
    with get_db() as db:
        items = db.execute(sql, args).fetchall()
    return render_template("orders.html", orders=items, query=q, selected_status=status)

@app.route("/orders/<int:order_id>")
@login_required()
def receipt(order_id):
    with get_db() as db:
        order = db.execute("SELECT o.*, r.receipt_number, r.issued_at FROM orders o LEFT JOIN receipts r ON r.order_id=o.id WHERE o.id=?", (order_id,)).fetchone()
        if not order:
            flash("Order not found.", "error")
            return redirect(url_for("orders"))
        lines = db.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
    return render_template("receipt.html", order=order, items=lines)

@app.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required("admin", "warehouse")
def update_status(order_id):
    status = request.form.get("status", "")
    if status not in ("Pending", "Preparing", "Completed"):
        flash("Choose a valid fulfillment status.", "error")
        return redirect(url_for("orders"))
    with get_db() as db:
        db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        db.commit()
    flash("Delivery fulfillment status updated.", "success")
    return redirect(request.referrer or url_for("orders"))

@app.route("/checklist")
@login_required("admin", "warehouse", "cashier")
def checklist():
    with get_db() as db:
        orders = db.execute("SELECT * FROM orders WHERE status!='Completed' ORDER BY delivery_date, id").fetchall()
        order_data = []
        for o in orders:
            items = db.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (o["id"],)).fetchall()
            order_data.append({"order": o, "items": items})
    return render_template("checklist.html", order_data=order_data)

@app.route("/reports")
@login_required("admin")
def reports():
    with get_db() as db:
        daily = db.execute("""
            SELECT substr(created_at,1,10) AS day, COUNT(*) AS count, SUM(total) AS amount
            FROM orders GROUP BY substr(created_at,1,10) ORDER BY day DESC LIMIT 14
        """).fetchall()
        best = db.execute("""
            SELECT product_name, SUM(quantity) AS units, SUM(line_total) AS amount
            FROM order_items GROUP BY product_name ORDER BY units DESC LIMIT 5
        """).fetchall()
        totals = db.execute("""
            SELECT COUNT(*) AS orders, COALESCE(SUM(total),0) AS sales,
                   COALESCE(AVG(total),0) AS average
            FROM orders WHERE status='Completed'
        """).fetchone()
    return render_template("reports.html", daily=daily, best=best, totals=totals)

@app.route("/help")
@login_required()
def help_page():
    return render_template("help.html")

   init_db()

   if __name__ == "__main__":
       app.run(debug=True)
