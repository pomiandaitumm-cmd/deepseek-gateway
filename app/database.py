import sqlite3
import hashlib
import random
import os
import time
from datetime import datetime, timezone

_default_docker = "/app/data/db.sqlite3"
_default_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db.sqlite3")
_in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER", "") == "1"
_fallback = _default_docker if _in_docker else _default_local
DB_PATH = os.environ.get("DB_PATH", _fallback)

def _ensure_data_dir():
    data_dir = os.path.dirname(DB_PATH)
    if data_dir: os.makedirs(data_dir, exist_ok=True)

def get_db():
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    _ensure_data_dir()
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT NOT NULL UNIQUE,
            key_prefix TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
            token_quota_total INTEGER NOT NULL DEFAULT 10000,
            token_quota_used INTEGER NOT NULL DEFAULT 0,
            request_quota_total INTEGER,
            request_quota_used INTEGER DEFAULT 0,
            allowed_models TEXT DEFAULT 'deepseek-v4-flash',
            package_name TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_used_at TEXT
        );
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER NOT NULL,
            key_prefix TEXT NOT NULL,
            model TEXT,
            provider TEXT DEFAULT 'deepseek',
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            status_code INTEGER,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        );
        CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
        CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
        CREATE INDEX IF NOT EXISTS idx_usage_api_key_id ON usage_logs(api_key_id);
        CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_logs(created_at);

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            telegram_or_discord TEXT DEFAULT '',
            use_case TEXT DEFAULT '',
            expected_daily_tokens INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token_quota INTEGER NOT NULL,
            rate_limit INTEGER DEFAULT 30,
            price_usd REAL DEFAULT 0,
            allowed_models TEXT DEFAULT 'deepseek-v4-flash',
            description TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            payment_status TEXT DEFAULT 'unpaid',
            key_prefix TEXT,
            price_usd REAL DEFAULT 0,
            source TEXT DEFAULT '',
            ref TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (package_id) REFERENCES packages(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            tx_hash TEXT NOT NULL UNIQUE,
            from_address TEXT DEFAULT '',
            to_address TEXT DEFAULT '',
            amount REAL DEFAULT 0,
            token_symbol TEXT DEFAULT 'USDT',
            network TEXT DEFAULT 'TRC20',
            confirmed_at TEXT DEFAULT '',
            raw_json TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );
        CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
        CREATE INDEX IF NOT EXISTS idx_payments_tx ON payments(tx_hash);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
    """)
    conn.commit()
    _migrate_add(conn, "api_keys", "token_quota_total", "INTEGER NOT NULL DEFAULT 10000")
    _migrate_add(conn, "api_keys", "token_quota_used", "INTEGER NOT NULL DEFAULT 0")
    _migrate_add(conn, "api_keys", "request_quota_total", "INTEGER")
    _migrate_add(conn, "api_keys", "request_quota_used", "INTEGER DEFAULT 0")
    _migrate_add(conn, "api_keys", "allowed_models", "TEXT DEFAULT 'deepseek-v4-flash'")
    _migrate_add(conn, "api_keys", "package_name", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "payment_status", "TEXT DEFAULT 'unpaid'")
    _migrate_add(conn, "orders", "price_usd", "REAL DEFAULT 0")
    _migrate_add(conn, "orders", "source", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "ref", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "note", "TEXT DEFAULT ''")
    _migrate_add(conn, "packages", "price_usd", "REAL DEFAULT 0")
    _migrate_add(conn, "packages", "allowed_models", "TEXT DEFAULT 'deepseek-v4-flash'")
    _migrate_add(conn, "orders", "payment_address", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "payment_network", "TEXT DEFAULT 'TRC20'")
    _migrate_add(conn, "orders", "expected_amount", "REAL DEFAULT 0")
    _migrate_add(conn, "orders", "paid_amount", "REAL DEFAULT 0")
    _migrate_add(conn, "orders", "tx_hash", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "expires_at", "TEXT")
    _migrate_add(conn, "orders", "paid_at", "TEXT")
    _migrate_add(conn, "orders", "issued_key", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "key_shown", "INTEGER DEFAULT 0")
    _migrate_add(conn, "orders", "paypal_order_id", "TEXT DEFAULT ''")
    _migrate_add(conn, "orders", "payment_provider", "TEXT DEFAULT ''")
    _seed_packages(conn)
    conn.close()


def _seed_packages(conn):
    """Seed v0.5 packages with pricing and model restrictions."""
    existing = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    if existing == 0:
        now = now_utc()
        pkgs = [
            ("Trial",      1000000,  30,  1.0,  "deepseek-v4-flash", "Quick test"),
            ("Starter",    5000000,  30,  3.0,  "deepseek-v4-flash", "Personal projects"),
            ("Standard",   12000000, 60,  6.0,  "deepseek-v4-flash", "Team / indie devs"),
            ("Pro",        2000000, 30,  6.0, "deepseek-v4-flash,deepseek-v4-pro", "Production + reasoning"),
        ]
        for name, quota, rl, price, models, desc in pkgs:
            conn.execute(
                "INSERT INTO packages (name,token_quota,rate_limit,price_usd,allowed_models,description,created_at) VALUES (?,?,?,?,?,?,?)",
                (name, quota, rl, price, models, desc, now))
        conn.commit()
    elif existing == 4:
        # Upgrade existing v0.3/v0.4 packages to v0.5 pricing
        upgrades = [
            (1, "Trial",    1000000,  30,  1.0,  "deepseek-v4-flash", "Quick test"),
            (2, "Starter",  5000000,  30,  3.0,  "deepseek-v4-flash", "Personal projects"),
            (3, "Standard", 12000000, 60,  6.0,  "deepseek-v4-flash", "Team / indie devs"),
            (4, "Pro",      2000000, 30,  6.0, "deepseek-v4-flash,deepseek-v4-pro", "Production + reasoning"),
        ]
        for pid, name, quota, rl, price, models, desc in upgrades:
            conn.execute(
                "UPDATE packages SET name=?, token_quota=?, rate_limit=?, price_usd=?, allowed_models=?, description=? WHERE id=?",
                (name, quota, rl, price, models, desc, pid))
        conn.commit()

def _migrate_add(conn, table, column, col_def):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        conn.commit()

def hash_key(key): return hashlib.sha256(key.encode()).hexdigest()
def now_utc(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def lookup_key(key):
    h = hash_key(key)
    conn = get_db()
    row = conn.execute("SELECT * FROM api_keys WHERE key_hash=?", (h,)).fetchone()
    conn.close()
    return dict(row) if row else None

def touch_key(key_id):
    conn = get_db()
    conn.execute("UPDATE api_keys SET last_used_at=? WHERE id=?", (now_utc(), key_id))
    conn.commit(); conn.close()

def log_usage(key_id, key_prefix, model, usage, status_code=200, error_message=None):
    conn = get_db()
    conn.execute("""
        INSERT INTO usage_logs (api_key_id, key_prefix, model, provider,
            prompt_tokens, completion_tokens, total_tokens, status_code, error_message, created_at)
        VALUES (?,?,?,'deepseek',?,?,?,?,?,?)
    """, (key_id, key_prefix, model,
        usage.get("prompt_tokens",0) if usage else 0,
        usage.get("completion_tokens",0) if usage else 0,
        usage.get("total_tokens",0) if usage else 0,
        status_code, error_message, now_utc()))
    conn.commit(); conn.close()

def check_rate_limit(key_id, limit_per_minute):
    if limit_per_minute <= 0: return True
    conn = get_db()
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    row = conn.execute("SELECT COUNT(*) as cnt FROM usage_logs WHERE api_key_id=? AND created_at >= datetime(?, '-60 seconds')", (key_id, cutoff)).fetchone()
    conn.close()
    return row["cnt"] < limit_per_minute


def get_key_usage(key_id):
    """Return usage stats for a given key_id."""
    conn = get_db()
    row = conn.execute("""
        SELECT k.key_prefix, k.name, k.status, k.token_quota_total, k.token_quota_used,
               k.rate_limit_per_minute, k.last_used_at, k.allowed_models, k.package_name,
               COUNT(l.id) as req_count
        FROM api_keys k
        LEFT JOIN usage_logs l ON l.api_key_id = k.id
        WHERE k.id = ?
        GROUP BY k.id
    """, (key_id,)).fetchone()
    conn.close()
    if not row:
        return None
    qt = row["token_quota_total"] or 0
    qu = row["token_quota_used"] or 0
    return {
        "prefix": row["key_prefix"],
        "name": row["name"],
        "status": row["status"],
        "total_quota": qt if qt > 0 else 0,
        "used_quota": qu,
        "remaining_quota": max(0, qt - qu),
        "request_count": row["req_count"],
        "last_used": row["last_used_at"],
        "rate_limit": row["rate_limit_per_minute"],
        "allowed_models": (row["allowed_models"] or "deepseek-v4-flash").split(","),
        "package": row["package_name"] or "",
    }

def create_order(customer_email, telegram_or_discord, use_case, expected_daily_tokens, package_id, source="", ref=""):
    """Create a customer+order from application. Returns order dict."""
    conn = get_db()
    now = now_utc()
    cust = conn.execute("SELECT id FROM customers WHERE email=?", (customer_email,)).fetchone()
    if cust:
        cust_id = cust["id"]
        conn.execute("UPDATE customers SET telegram_or_discord=?, use_case=?, expected_daily_tokens=? WHERE id=?",
                     (telegram_or_discord, use_case, expected_daily_tokens, cust_id))
    else:
        cur = conn.execute("INSERT INTO customers (email,telegram_or_discord,use_case,expected_daily_tokens,created_at) VALUES (?,?,?,?,?)",
                           (customer_email, telegram_or_discord, use_case, expected_daily_tokens, now))
        cust_id = cur.lastrowid
    pkg_price = conn.execute("SELECT price_usd FROM packages WHERE id=?", (package_id,)).fetchone()
    price = pkg_price["price_usd"] if pkg_price else 0
    cur = conn.execute("INSERT INTO orders (customer_id,package_id,status,payment_status,price_usd,source,ref,created_at) VALUES (?,?,'pending','unpaid',?,?,?,?)",
                 (cust_id, package_id, price, source, ref, now))
    order_id = cur.lastrowid
    conn.commit()
    pkg = conn.execute("SELECT * FROM packages WHERE id=?", (package_id,)).fetchone()
    conn.close()
    return {
        "order_id": order_id,
        "status": "pending",
        "customer_email": customer_email,
        "package_name": pkg["name"] if pkg else "unknown",
        "token_quota": pkg["token_quota"] if pkg else 0,
        "price_usd": price if pkg else 0,
    }

def get_order(order_id):
    conn = get_db()
    row = conn.execute("""
        SELECT o.*, c.email, p.name as package_name, p.token_quota, p.rate_limit
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN packages p ON p.id = o.package_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_orders(status=None):
    conn = get_db()
    q = """
        SELECT o.*, c.email, c.telegram_or_discord, p.name as package_name, p.token_quota, p.allowed_models, o.source, o.ref, o.note, o.price_usd
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN packages p ON p.id = o.package_id
    """
    if status:
        q += " WHERE o.status = ?"
        rows = conn.execute(q + " ORDER BY o.created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute(q + " ORDER BY o.created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def list_customers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM customers ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_order_status(order_id, email):
    """Public order status lookup. Returns key info only when approved."""
    conn = get_db()
    row = conn.execute("""
        SELECT o.id, o.status, o.payment_status, o.key_prefix, o.created_at, o.approved_at,
               c.email, p.name as package_name, p.token_quota, p.rate_limit, p.allowed_models, p.price_usd
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN packages p ON p.id = o.package_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()
    conn.close()
    if not row:
        return None, "Order not found"
    if row["email"].lower() != email.lower():
        return None, "Email does not match this order"
    result = {
        "order_id": row["id"],
        "status": row["status"],
        "payment_status": row["payment_status"] or "unpaid",
        "selected_plan": row["package_name"],
        "quota": row["token_quota"],
        "rate_limit": row["rate_limit"],
        "allowed_models": (row["allowed_models"] or "deepseek-v4-flash").split(","),
        "price_usd": row["price_usd"] or 0,
        "created_at": row["created_at"],
        "approved_at": row["approved_at"],
        "key_prefix": None,
        "full_key": row["issued_key"] if (row["status"] == "approved" and row["issued_key"]) else None,
        "dashboard_url": None,
        "message": None,
    }
    if row["status"] == "approved" and row["key_prefix"]:
        result["key_prefix"] = row["key_prefix"]
        result["dashboard_url"] = "http://65.49.201.211/dashboard.html"
        result["message"] = "Your key was displayed when the order was approved. If you lost it, contact support."
    elif row["status"] == "pending" and (row["payment_status"] or "unpaid") == "unpaid":
        result["message"] = "Your order is pending review. We will contact you at your email."
    elif row["status"] == "pending" and (row["payment_status"] or "") == "paid":
        result["message"] = "Payment received. Waiting for admin approval."
    return result, None

def mark_order_paid(order_id, note=""):
    """Mark an order as paid. Only works on pending orders."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return None, "Order not found"
    if order["status"] != "pending":
        conn.close()
        return None, f"Order status is '{order['status']}', expected 'pending'"
    now = now_utc()
    conn.execute("UPDATE orders SET payment_status='paid', approved_at=? WHERE id=?", (now, order_id))
    conn.commit()
    o = conn.execute("""
        SELECT o.*, c.email, p.name as pkg_name
        FROM orders o JOIN customers c ON c.id=o.customer_id JOIN packages p ON p.id=o.package_id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    conn.close()
    return {
        "order_id": order_id,
        "status": o["status"],
        "payment_status": "paid",
        "email": o["email"],
        "package": o["pkg_name"],
        "note": note,
    }, None

def approve_order(order_id):
    """Approve an order: set approved, create api_key, set key_prefix on order.
    Accepts pending or paid orders."""
    import secrets, string, hashlib
    conn = get_db()
    order = conn.execute("SELECT o.*, p.token_quota, p.rate_limit, p.name as pkg_name, p.allowed_models, c.email as customer_name "
                         "FROM orders o JOIN packages p ON p.id=o.package_id JOIN customers c ON c.id=o.customer_id "
                         "WHERE o.id=?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return None, "Order not found"
    if order["status"] not in ("pending", "paid"):
        conn.close()
        return None, f"Order status is '{order['status']}', not 'pending' or 'paid'"
    a = string.ascii_letters + string.digits
    fk = "sk-gateway-" + "".join(secrets.choice(a) for _ in range(48))
    kh = hashlib.sha256(fk.encode()).hexdigest()
    kp = fk[:16]
    now = now_utc()
    allowed = order["allowed_models"] if order["allowed_models"] else "deepseek-v4-flash"
    pkg_name = order["pkg_name"] if order["pkg_name"] else ""
    conn.execute("INSERT INTO api_keys (key_hash,key_prefix,name,status,rate_limit_per_minute,token_quota_total,allowed_models,package_name,created_at) VALUES (?,?,?,'active',?,?,?,?,?)",
                 (kh, kp, order["customer_name"], order["rate_limit"], order["token_quota"], allowed, pkg_name, now))
    conn.execute("UPDATE orders SET status='approved', key_prefix=?, issued_key=?, approved_at=? WHERE id=?",
                 (kp, fk, now, order_id))
    conn.commit()
    conn.close()
    return {
        "order_id": order_id,
        "status": "approved",
        "key_prefix": kp,
        "full_key": fk,
        "name": order["customer_name"],
        "token_quota": order["token_quota"],
        "rate_limit": order["rate_limit"],
    }, None

def check_quota(key_info):
    total = key_info.get("token_quota_total", 0)
    used = key_info.get("token_quota_used", 0)
    if total == 0 or total is None: return True
    return used < total

def deduct_quota(key_id, tokens):
    if tokens <= 0: return
    conn = get_db()
    conn.execute("UPDATE api_keys SET token_quota_used=token_quota_used+? WHERE id=?", (tokens, key_id))
    conn.commit(); conn.close()

def get_lead_stats():
    """Return order counts grouped by source channel."""
    conn = get_db()
    rows = conn.execute("""
        SELECT 
            CASE WHEN source IS NULL OR source = '' THEN 'direct'
                 ELSE source END as channel,
            COUNT(*) as cnt
        FROM orders
        GROUP BY channel
        ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    total = sum(r["cnt"] for r in rows)
    return {
        "total": total,
        "channels": [{"channel": r["channel"], "count": r["cnt"]} for r in rows]
    }

# ===== v0.7 Payment System =====



# Payment config (loaded from env, with defaults)
PAYMENT_ADDRESS = os.environ.get("PAYMENT_ADDRESS", "PLACEHOLDER_TRC20_ADDRESS")
PAYMENT_NETWORK = os.environ.get("PAYMENT_NETWORK", "TRC20")
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "USDT")
TRONGRID_API_BASE = os.environ.get("TRONGRID_API_BASE", "https://api.trongrid.io")
PAYMENT_POLL_INTERVAL = int(os.environ.get("PAYMENT_POLL_INTERVAL", "30"))
ORDER_EXPIRY_MINUTES = int(os.environ.get("ORDER_EXPIRY_MINUTES", "30"))


def _generate_unique_cents(order_id, price_usd):
    """Generate a unique sub-dollar amount for this order to enable payment matching.
    Uses order_id to seed uniqueness with a small random offset.
    Returns expected_amount as float."""
    random.seed(f"{order_id}-{time.time_ns()}")
    # Use order_id * 0.0001 + random micro-adjustment for uniqueness
    base_cents = (order_id * 7 + 13) % 100  # deterministic part
    micro = random.randint(1, 99) / 10000
    unique_cents = base_cents + micro
    expected = price_usd + (unique_cents / 100)
    return round(expected, 6)


def checkout_order(customer_email, plan_name, source="", ref=""):
    """Create a checkout order with payment details. Returns order dict."""
    conn = get_db()
    now = now_utc()
    pkg = conn.execute("SELECT * FROM packages WHERE name=? AND is_active=1", (plan_name,)).fetchone()
    if not pkg:
        conn.close()
        return None, f"Package '{plan_name}' not found"
    package_id = pkg["id"]
    price = pkg["price_usd"]
    quota = pkg["token_quota"]
    models = pkg["allowed_models"] or "deepseek-v4-flash"

    # Find or create customer
    cust = conn.execute("SELECT id FROM customers WHERE email=?", (customer_email,)).fetchone()
    if cust:
        cust_id = cust["id"]
    else:
        cur = conn.execute("INSERT INTO customers (email,created_at) VALUES (?,?)", (customer_email, now))
        cust_id = cur.lastrowid

    # Generate unique amount
    cur = conn.execute("INSERT INTO orders (customer_id,package_id,status,payment_status,price_usd,source,ref,created_at) VALUES (?,?,'pending','unpaid',?,?,?,?)",
                       (cust_id, package_id, price, source, ref, now))
    order_id = cur.lastrowid
    expected_amount = _generate_unique_cents(order_id, price)
    expires_at_dt = datetime.now(timezone.utc)
    from datetime import timedelta as _td; expires_at_dt = expires_at_dt + _td(minutes=ORDER_EXPIRY_MINUTES)
    expires_at = expires_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute("""UPDATE orders SET payment_address=?, payment_network=?, expected_amount=?, expires_at=?
                    WHERE id=?""",
                 (PAYMENT_ADDRESS, PAYMENT_NETWORK, expected_amount, expires_at, order_id))
    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "status": "pending",
        "plan": plan_name,
        "token_quota": quota,
        "price_usd": price,
        "expected_amount": expected_amount,
        "payment_address": PAYMENT_ADDRESS,
        "payment_network": PAYMENT_NETWORK,
        "payment_token": PAYMENT_TOKEN,
        "expires_at": expires_at,
        "email": customer_email,
        "status_url": f"/order.html?order_id={order_id}",
        "message": "Send exact amount to the address below. Your key will appear automatically after payment is confirmed.",
    }, None


def get_order_status_v07(order_id, email):
    """v0.7 order status with payment info and auto-approve display."""
    conn = get_db()
    row = conn.execute("""
        SELECT o.*, c.email, p.name as package_name, p.token_quota, p.rate_limit, p.allowed_models
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN packages p ON p.id = o.package_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()
    conn.close()

    if not row:
        return None, "Order not found"
    if row["email"].lower() != email.lower():
        return None, "Email does not match this order"

    result = {
        "order_id": row["id"],
        "status": row["status"],
        "payment_status": row["payment_status"] or "unpaid",
        "selected_plan": row["package_name"],
        "quota": row["token_quota"],
        "rate_limit": row["rate_limit"],
        "allowed_models": (row["allowed_models"] or "deepseek-v4-flash").split(","),
        "price_usd": row["price_usd"] or 0,
        "expected_amount": row["expected_amount"] or 0,
        "payment_address": row["payment_address"] or "",
        "payment_network": row["payment_network"] or "TRC20",
        "expires_at": row["expires_at"],
        "tx_hash": row["tx_hash"] or "",
        "created_at": row["created_at"],
        "approved_at": row["approved_at"],
        "key_prefix": row["key_prefix"] or None,
        "full_key": row["issued_key"] if (row["status"] == "approved" and row["issued_key"]) else None,
        "dashboard_url": None,
        "message": None,
    }

    if row["status"] == "approved" and row["key_prefix"]:
        result["key_prefix"] = row["key_prefix"]
        result["dashboard_url"] = "http://65.49.201.211/dashboard.html"
        result["message"] = "Your key was displayed when the order was approved. If you lost it, contact support."
    elif row["status"] == "expired":
        result["message"] = "This order has expired. Please create a new order."
    elif row["status"] == "pending" and (row["payment_status"] or "unpaid") == "unpaid":
        result["message"] = "Waiting for payment. Send exact amount to the TRC20 address above."
    elif row["status"] == "pending" and (row["payment_status"] or "") == "paid":
        result["message"] = "Payment received. Generating your API key..."
    elif row["status"] == "paid":
        result["message"] = "Payment confirmed. Waiting for key generation."

    return result, None


def check_payment_match(expected_amount, tx_amount):
    """Check if a transaction amount matches the expected amount within tolerance."""
    return abs(tx_amount - expected_amount) < 0.01


def process_payment(order_id, tx_hash, from_address, to_address, amount, raw_json=""):
    """Record a matched payment and auto-approve the order. Returns (result, error)."""
    conn = get_db()
    now = now_utc()

    # Check tx_hash not already used
    existing = conn.execute("SELECT id FROM payments WHERE tx_hash=?", (tx_hash,)).fetchone()
    if existing:
        conn.close()
        return None, f"tx_hash {tx_hash} already processed"

    order = conn.execute("SELECT * FROM orders WHERE id=? AND status='pending'", (order_id,)).fetchone()
    if not order:
        conn.close()
        return None, f"Order #{order_id} not found or not pending"

    # Record payment
    conn.execute("""INSERT INTO payments (order_id, tx_hash, from_address, to_address, amount, token_symbol, network, confirmed_at, raw_json, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                 (order_id, tx_hash, from_address, to_address, amount, PAYMENT_TOKEN, PAYMENT_NETWORK, now, raw_json, now))

    # Mark order as paid
    conn.execute("""UPDATE orders SET payment_status='paid', paid_amount=?, tx_hash=?, paid_at=?, status='paid'
                    WHERE id=?""", (amount, tx_hash, now, order_id))
    conn.commit()

    # Auto-approve
    result, err = approve_order(order_id)
    conn.close()

    if err:
        return None, f"Payment recorded but approve failed: {err}"
    return {
        "order_id": order_id,
        "tx_hash": tx_hash,
        "amount": amount,
        "key_prefix": result["key_prefix"],
        "full_key": result["full_key"],
        "status": "approved",
    }, None


def get_pending_orders():
    """Return all pending orders that haven't expired."""
    conn = get_db()
    now = now_utc()
    rows = conn.execute("""
        SELECT o.*, p.name as pkg_name
        FROM orders o
        JOIN packages p ON p.id = o.package_id
        WHERE o.status = 'pending'
          AND (o.expires_at IS NULL OR o.expires_at > ?)
    """, (now,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def expire_stale_orders():
    """Expire orders past their expires_at time."""
    conn = get_db()
    now = now_utc()
    cur = conn.execute("UPDATE orders SET status='expired' WHERE status='pending' AND expires_at IS NOT NULL AND expires_at < ?", (now,))
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


# ===== v0.8 PayPal Integration =====

def checkout_order_paypal(customer_email, plan_name, paypal_order_id, source="", ref=""):
    """Create a checkout order linked to a PayPal order. Returns order dict."""
    conn = get_db()
    now = now_utc()
    pkg = conn.execute("SELECT * FROM packages WHERE name=? AND is_active=1", (plan_name,)).fetchone()
    if not pkg:
        conn.close()
        return None, f"Package '{plan_name}' not found"
    package_id = pkg["id"]
    price = pkg["price_usd"]
    quota = pkg["token_quota"]

    # Find or create customer
    cust = conn.execute("SELECT id FROM customers WHERE email=?", (customer_email,)).fetchone()
    if cust:
        cust_id = cust["id"]
    else:
        cur = conn.execute("INSERT INTO customers (email,created_at) VALUES (?,?)", (customer_email, now))
        cust_id = cur.lastrowid

    # Create order with PayPal linkage
    cur = conn.execute(
        "INSERT INTO orders (customer_id,package_id,status,payment_status,price_usd,source,ref,paypal_order_id,payment_provider,created_at) VALUES (?,?,'pending','unpaid',?,?,?,?,?,?)",
        (cust_id, package_id, price, source, ref, paypal_order_id, "paypal", now))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "status": "pending",
        "plan": plan_name,
        "token_quota": quota,
        "price_usd": price,
        "paypal_order_id": paypal_order_id,
        "email": customer_email,
        "status_url": f"/order.html?order_id={order_id}",
        "message": "PayPal order created. Complete payment to get your API key.",
    }, None


def capture_paypal_and_approve(local_order_id, paypal_order_id, payer_email=""):
    """After PayPal capture succeeds: mark order paid, auto-approve, generate key.
    Prevents duplicate key issuance: if already approved, returns existing key."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (local_order_id,)).fetchone()
    if not order:
        conn.close()
        return None, "Order not found"

    # Prevent double-issuance
    if order["status"] == "approved" and order["issued_key"]:
        pkg = conn.execute("SELECT * FROM packages WHERE id=?", (order["package_id"],)).fetchone()
        conn.close()
        return {
            "order_id": local_order_id,
            "status": "approved",
            "key_prefix": order["key_prefix"],
            "full_key": order["issued_key"],
            "token_quota": pkg["token_quota"] if pkg else 0,
            "message": "Key already issued for this order.",
        }, None

    if order["status"] not in ("pending", "paid"):
        conn.close()
        return None, f"Order status is '{order['status']}', cannot capture"

    now = now_utc()
    # Mark as paid
    conn.execute("""UPDATE orders SET payment_status='paid', paid_at=?, status='paid'
                    WHERE id=?""", (now, local_order_id))
    conn.commit()
    conn.close()

    # Auto-approve
    return approve_order(local_order_id)


def get_order_status_v08(order_id, email):
    """v0.8 order status with PayPal payment info."""
    conn = get_db()
    row = conn.execute("""
        SELECT o.*, c.email, p.name as package_name, p.token_quota, p.rate_limit, p.allowed_models
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN packages p ON p.id = o.package_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()
    conn.close()

    if not row:
        return None, "Order not found"
    if row["email"].lower() != email.lower():
        return None, "Email does not match this order"

    result = {
        "order_id": row["id"],
        "status": row["status"],
        "payment_status": row["payment_status"] or "unpaid",
        "payment_provider": row["payment_provider"] or "",
        "paypal_order_id": row["paypal_order_id"] or "",
        "selected_plan": row["package_name"],
        "quota": row["token_quota"],
        "rate_limit": row["rate_limit"],
        "allowed_models": (row["allowed_models"] or "deepseek-v4-flash").split(","),
        "price_usd": row["price_usd"] or 0,
        "created_at": row["created_at"],
        "approved_at": row["approved_at"],
        "key_prefix": row["key_prefix"] or None,
        "full_key": row["issued_key"] if (row["status"] == "approved" and row["issued_key"]) else None,
        "dashboard_url": None,
        "message": None,
    }

    if row["status"] == "approved" and row["key_prefix"]:
        result["key_prefix"] = row["key_prefix"]
        result["dashboard_url"] = f"{SITE_BASE_URL}/dashboard.html" if 'SITE_BASE_URL' in dir() else "http://65.49.201.211/dashboard.html"
        result["message"] = "Your API key is ready. Save it now and go to Dashboard to check usage."
    elif row["status"] == "expired":
        result["message"] = "This order has expired. Please create a new order."
    elif row["status"] in ("pending", "paid") and (row["payment_status"] or "unpaid") == "paid":
        result["message"] = "Payment received. Generating your API key..."
    elif row["status"] == "pending" and (row["payment_status"] or "unpaid") == "unpaid":
        result["message"] = "Waiting for PayPal payment. Complete your payment to receive your API key."

    return result, None