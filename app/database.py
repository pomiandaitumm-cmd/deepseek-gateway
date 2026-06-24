import sqlite3
import hashlib
import random
import os
import json
import time
from datetime import datetime, timezone

_default_docker = "/app/data/db.sqlite3"
_default_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db.sqlite3")
_in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER", "") == "1"
_fallback = _default_docker if _in_docker else _default_local
DB_PATH = os.environ.get("DB_PATH", _fallback)

def parse_allowed_models(val):
    if not val:
        return ['deepseek-v4-flash']
    if isinstance(val, list):
        return val
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [m.strip() for m in str(val).split(',') if m.strip()]

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
            # (name, token_quota, rate_limit, price_usd, allowed_models, description, sale_price, upstream_budget, currency)
            ("Trial",      2000000,  30,  0.99,  "deepseek-v4-flash,deepseek-v4-pro", "Quick test. Pay $0.99, get $0.74 API budget.", 0.99, 0.74, "USD"),
            ("Starter",    10000000,  30,  2.49,  "deepseek-v4-flash,deepseek-v4-pro", "Personal projects. Pay $2.49, get $1.87 API budget.", 2.49, 1.87, "USD"),
            ("Standard",   20000000, 60,  4.99,  "deepseek-v4-flash,deepseek-v4-pro", "Team / indie devs. Pay $4.99, get $3.74 API budget.", 4.99, 3.74, "USD"),
            ("Pro",        5000000, 30,  5.99, "deepseek-v4-flash,deepseek-v4-pro", "Production. Pay $5.99, get $4.49 API budget.", 5.99, 4.49, "USD"),
        ]
        for name, quota, rl, price, models, desc, sale_price, upstream_budget, currency in pkgs:
            conn.execute(
                "INSERT INTO packages (name,token_quota,rate_limit,price_usd,allowed_models,description,sale_price,upstream_budget,currency,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (name, quota, rl, price, models, desc, sale_price, upstream_budget, currency, now))
        conn.commit()
    elif existing >= 4:
        # Upgrade existing packages to v0.9 budget-based pricing
        upgrades = [
            (1, "Trial",    2000000,  30,  0.99,  "deepseek-v4-flash,deepseek-v4-pro", "Quick test. Pay $0.99, get $0.74 API budget.", 0.99, 0.74, "USD"),
            (2, "Starter",  10000000,  30,  2.49,  "deepseek-v4-flash,deepseek-v4-pro", "Personal projects. Pay $2.49, get $1.87 API budget.", 2.49, 1.87, "USD"),
            (3, "Standard", 20000000, 60,  4.99,  "deepseek-v4-flash,deepseek-v4-pro", "Team / indie devs. Pay $4.99, get $3.74 API budget.", 4.99, 3.74, "USD"),
            (4, "Pro",      5000000, 30,  5.99, "deepseek-v4-flash,deepseek-v4-pro", "Production. Pay $5.99, get $4.49 API budget.", 5.99, 4.49, "USD"),
        ]
        for pid, name, quota, rl, price, models, desc, sale_price, upstream_budget, currency in upgrades:
            conn.execute(
                "UPDATE packages SET name=?, token_quota=?, rate_limit=?, price_usd=?, allowed_models=?, description=?, sale_price=?, upstream_budget=?, currency=? WHERE id=?",
                (name, quota, rl, price, models, desc, sale_price, upstream_budget, currency, pid))
        conn.commit()

def _migrate_add(conn, table, column, col_def):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        conn.commit()



# --- Pricing: per-token cost in USD (DeepSeek official rates) ---
MODEL_PRICING = {
    "deepseek-v4-flash": {
        "cache_miss_input": 0.00000014,   # $0.14 / 1M tokens
        "cache_hit_input":  0.000000014,  # $0.014 / 1M tokens
        "output":           0.00000028,   # $0.28 / 1M tokens
    },
    "deepseek-v4-pro": {
        "cache_miss_input": 0.00000027,   # $0.27 / 1M tokens
        "cache_hit_input":  0.000000027,  # $0.027 / 1M tokens
        "output":           0.00000087,   # $0.87 / 1M tokens
    },
}

def calculate_upstream_cost(model, usage):
    """Calculate upstream cost in USD from DeepSeek usage response.
    Uses cache_hit_tokens, cache_miss_tokens, completion_tokens from usage."""
    if not usage or not model:
        return 0.0
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Fallback: use flash pricing
        pricing = MODEL_PRICING["deepseek-v4-flash"]
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    cache_hit = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) or usage.get("prompt_cache_hit_tokens", 0) or 0
    cache_miss = max(0, prompt_tokens - cache_hit)
    completion = usage.get("completion_tokens", 0) or 0
    cost = (cache_miss * pricing["cache_miss_input"] +
            cache_hit * pricing["cache_hit_input"] +
            completion * pricing["output"])
    return round(cost, 8)

def hash_key(key): return hashlib.sha256(key.encode()).hexdigest()
def now_utc(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def lookup_key(key):
    h = hash_key(key)
    conn = get_db()
    row = conn.execute("SELECT * FROM api_keys WHERE key_hash=?", (h,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["allowed_models"] = parse_allowed_models(d.get("allowed_models"))
    return d

def touch_key(key_id):
    conn = get_db()
    conn.execute("UPDATE api_keys SET last_used_at=? WHERE id=?", (now_utc(), key_id))
    conn.commit(); conn.close()

def log_usage(key_id, key_prefix, model, usage, status_code=200, error_message=None, upstream_cost=0.0):
    conn = get_db()
    prompt_tokens = usage.get("prompt_tokens", 0) if usage else 0
    completion_tokens = usage.get("completion_tokens", 0) if usage else 0
    total_tokens = usage.get("total_tokens", 0) if usage else 0
    prompt_details = usage.get("prompt_tokens_details", {}) if usage else {}
    cache_hit = prompt_details.get("cached_tokens", 0) or usage.get("prompt_cache_hit_tokens", 0) or 0 if usage else 0
    cache_miss = max(0, prompt_tokens - cache_hit) if usage else 0
    conn.execute("""
        INSERT INTO usage_logs (api_key_id, key_prefix, model, provider,
            prompt_tokens, completion_tokens, total_tokens,
            cache_hit_tokens, cache_miss_tokens, upstream_cost,
            status_code, error_message, created_at)
        VALUES (?,?,?,'deepseek',?,?,?,?,?,?,?,?,?)
    """, (key_id, key_prefix, model,
        prompt_tokens, completion_tokens, total_tokens,
        cache_hit, cache_miss, upstream_cost,
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
    """Return usage stats for a given key_id with budget-based metrics."""
    conn = get_db()
    row = conn.execute("""
        SELECT k.key_prefix, k.name, k.status, k.token_quota_total, k.token_quota_used,
               k.upstream_budget, k.upstream_cost_used, k.sale_price, k.currency,
               k.rate_limit_per_minute, k.last_used_at, k.allowed_models, k.package_name,
               COUNT(l.id) as req_count,
               SUM(l.cache_hit_tokens) as total_cache_hit,
               SUM(l.cache_miss_tokens) as total_cache_miss,
               SUM(l.completion_tokens) as total_output,
               SUM(l.total_tokens) as total_all_tokens
        FROM api_keys k
        LEFT JOIN usage_logs l ON l.api_key_id = k.id
        WHERE k.id = ?
        GROUP BY k.id
    """, (key_id,)).fetchone()
    conn.close()
    if not row:
        return None
    budget = row["upstream_budget"] or 0
    used_cost = row["upstream_cost_used"] or 0
    remaining = max(0, budget - used_cost)
    # Get last usage breakdown
    conn2 = get_db()
    last_log = conn2.execute(
        "SELECT cache_hit_tokens, cache_miss_tokens, completion_tokens, total_tokens, upstream_cost FROM usage_logs WHERE api_key_id=? ORDER BY id DESC LIMIT 1",
        (key_id,)).fetchone()
    conn2.close()

    last_usage = None
    if last_log:
        last_usage = {
            "prompt_cache_hit_tokens": last_log["cache_hit_tokens"] or 0,
            "prompt_cache_miss_tokens": last_log["cache_miss_tokens"] or 0,
            "completion_tokens": last_log["completion_tokens"] or 0,
            "total_tokens": last_log["total_tokens"] or 0,
            "upstream_cost": str(round(last_log["upstream_cost"] or 0, 8)),
        }

    return {
        "prefix": row["key_prefix"],
        "name": row["name"],
        "status": row["status"],
        "sale_price": row["sale_price"] or 0,
        "currency": row["currency"] or "USD",
        "upstream_budget": budget,
        "used_upstream_cost": round(used_cost, 8),
        "remaining_budget": round(remaining, 8),
        "request_count": row["req_count"],
        "last_used": row["last_used_at"],
        "rate_limit": row["rate_limit_per_minute"],
        "allowed_models": parse_allowed_models(row["allowed_models"]),
        "package": row["package_name"] or "",
        "cache_hit_tokens": row["total_cache_hit"] or 0,
        "cache_miss_tokens": row["total_cache_miss"] or 0,
        "output_tokens": row["total_output"] or 0,
        "total_tokens": row["total_all_tokens"] or 0,
        "last_usage": last_usage,
        # Legacy fields for backward compat
        "total_quota": row["token_quota_total"] or 0,
        "used_quota": row["token_quota_used"] or 0,
        "remaining_quota": max(0, (row["token_quota_total"] or 0) - (row["token_quota_used"] or 0)),
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
        "allowed_models": parse_allowed_models(row["allowed_models"]),
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
        result["dashboard_url"] = f"{SITE_BASE_URL}/dashboard.html"
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
    order = conn.execute("SELECT o.*, p.token_quota, p.rate_limit, p.name as pkg_name, p.allowed_models, p.sale_price, p.upstream_budget, p.currency, c.email as customer_name "
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
    sale_price = order["sale_price"] if order["sale_price"] else order["price_usd"] or 0
    upstream_budget = order["upstream_budget"] if order["upstream_budget"] else 0
    currency = order["currency"] if order["currency"] else "USD"
    conn.execute("INSERT INTO api_keys (key_hash,key_prefix,name,status,rate_limit_per_minute,token_quota_total,allowed_models,package_name,sale_price,upstream_budget,currency,created_at) VALUES (?,?,?,'active',?,?,?,?,?,?,?,?)",
                 (kh, kp, order["customer_name"], order["rate_limit"], order["token_quota"], allowed, pkg_name, sale_price, upstream_budget, currency, now))
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
        "upstream_budget": upstream_budget,
        "sale_price": sale_price,
        "currency": currency,
        "rate_limit": order["rate_limit"],
    }, None

def check_quota(key_info):
    """Check if key has remaining upstream budget. Returns True if can proceed."""
    budget = key_info.get("upstream_budget", 0) or 0
    if budget == 0:
        # Fallback to legacy token quota for backward compat
        total = key_info.get("token_quota_total", 0) or 0
        used = key_info.get("token_quota_used", 0) or 0
        if total == 0: return True
        return used < total
    used_cost = key_info.get("upstream_cost_used", 0) or 0
    remaining = budget - used_cost
    if remaining <= 0:
        # Mark key as exhausted if not already
        conn = get_db()
        conn.execute("UPDATE api_keys SET status='exhausted' WHERE id=? AND status='active'", (key_info["id"],))
        conn.commit(); conn.close()
        return False
    return True

def deduct_quota(key_id, tokens):
    """Legacy: deduct token quota. Kept for backward compat."""
    if tokens <= 0: return
    conn = get_db()
    conn.execute("UPDATE api_keys SET token_quota_used=token_quota_used+? WHERE id=?", (tokens, key_id))
    conn.commit(); conn.close()

def deduct_upstream_cost(key_id, cost):
    """Deduct upstream_cost from key's upstream_budget."""
    if cost <= 0: return
    conn = get_db()
    conn.execute("UPDATE api_keys SET upstream_cost_used=upstream_cost_used+? WHERE id=?", (cost, key_id))
    # Also update legacy token_quota for backward compat
    conn.execute("UPDATE api_keys SET token_quota_used=token_quota_used+? WHERE id=?", (int(cost * 1000000), key_id))
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
        "allowed_models": parse_allowed_models(row["allowed_models"]),
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
        result["dashboard_url"] = f"{SITE_BASE_URL}/dashboard.html"
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
        "allowed_models": parse_allowed_models(row["allowed_models"]),
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
        result["dashboard_url"] = f"{SITE_BASE_URL}/dashboard.html" if 'SITE_BASE_URL' in dir() else f"{SITE_BASE_URL}/dashboard.html"
        result["message"] = "Your API key is ready. Save it now and go to Dashboard to check usage."
    elif row["status"] == "expired":
        result["message"] = "This order has expired. Please create a new order."
    elif row["status"] in ("pending", "paid") and (row["payment_status"] or "unpaid") == "paid":
        result["message"] = "Payment received. Generating your API key..."
    elif row["status"] == "pending" and (row["payment_status"] or "unpaid") == "unpaid":
        result["message"] = "Waiting for PayPal payment. Complete your payment to receive your API key."

    return result, None

# ===== v0.9 Admin Backend =====

def get_admin_summary():
    """Return aggregate stats for admin dashboard."""
    conn = get_db()
    row = conn.execute("""
        SELECT
            COUNT(DISTINCT o.id) as total_orders,
            SUM(CASE WHEN o.payment_status='paid' THEN 1 ELSE 0 END) as paid_orders,
            SUM(CASE WHEN o.status='approved' THEN 1 ELSE 0 END) as approved_orders,
            COUNT(DISTINCT k.id) as total_keys,
            SUM(CASE WHEN k.status='active' THEN 1 ELSE 0 END) as active_keys,
            SUM(CASE WHEN k.status='exhausted' THEN 1 ELSE 0 END) as exhausted_keys,
            SUM(CASE WHEN k.status='disabled' THEN 1 ELSE 0 END) as disabled_keys,
            COALESCE(SUM(k.sale_price), 0) as total_sales,
            COALESCE(SUM(k.upstream_budget), 0) as total_budget,
            COALESCE(SUM(k.upstream_cost_used), 0) as total_used_cost
        FROM orders o
        LEFT JOIN api_keys k ON k.key_prefix = o.key_prefix
    """).fetchone()
    conn.close()
    if not row:
        return {"total_orders": 0, "paid_orders": 0, "approved_orders": 0,
                "total_keys": 0, "active_keys": 0, "exhausted_keys": 0, "disabled_keys": 0,
                "total_sales": 0, "total_budget": 0, "total_used_cost": 0, "theoretical_margin": 0}
    total_sales = row["total_sales"] or 0
    total_used = row["total_used_cost"] or 0
    return {
        "total_orders": row["total_orders"] or 0,
        "paid_orders": row["paid_orders"] or 0,
        "approved_orders": row["approved_orders"] or 0,
        "total_keys": row["total_keys"] or 0,
        "active_keys": row["active_keys"] or 0,
        "exhausted_keys": row["exhausted_keys"] or 0,
        "disabled_keys": row["disabled_keys"] or 0,
        "total_sales": round(total_sales, 2),
        "total_budget": round(row["total_budget"] or 0, 2),
        "total_used_cost": round(total_used, 8),
        "theoretical_margin": round(total_sales - total_used, 2),
    }


def get_admin_orders(search=None, status_filter=None):
    """Return all orders with customer/key info for admin dashboard."""
    conn = get_db()
    query = """
        SELECT o.id as order_id, c.email, p.name as package_name,
               p.sale_price, p.currency, COALESCE(o.status, CASE WHEN o.payment_status = 'paid' THEN 'approved' ELSE 'pending' END) as order_status,
               p.upstream_budget, COALESCE(k.upstream_cost_used, 0) as used_upstream_cost,
               (p.upstream_budget - COALESCE(k.upstream_cost_used, 0)) as remaining_budget,
               o.payment_provider, o.payment_status,
               o.key_prefix, COALESCE(k.status, 'pending') as key_status,
               COALESCE((SELECT COUNT(*) FROM usage_logs l WHERE l.api_key_id = k.id), 0) as requests,
               o.created_at, COALESCE(k.last_used_at, '') as last_used_at
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN packages p ON p.id = o.package_id
        LEFT JOIN api_keys k ON k.key_prefix = o.key_prefix
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (c.email LIKE ? OR o.key_prefix LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])
    if status_filter:
        if status_filter in ("active", "exhausted", "disabled"):
            query += " AND k.status = ?"
            params.append(status_filter)
        elif status_filter == "paid":
            query += " AND o.payment_status = 'paid'"
        elif status_filter == "unpaid":
            query += " AND (o.payment_status IS NULL OR o.payment_status != 'paid')"
        elif status_filter in ("pending", "approved"):
            query += " AND o.status = ?"
            params.append(status_filter)
    query += " ORDER BY o.id DESC LIMIT 200"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_admin_keys(search=None, status_filter=None):
    """Return all API keys with customer info for admin dashboard."""
    conn = get_db()
    query = """
        SELECT k.id, k.key_prefix, k.name, k.status,
               k.upstream_budget, k.upstream_cost_used,
               (COALESCE(k.upstream_budget,0) - COALESCE(k.upstream_cost_used,0)) as remaining_budget,
               k.sale_price, k.currency, k.allowed_models, k.package_name,
               k.rate_limit_per_minute, k.last_used_at,
               COUNT(l.id) as requests,
               COALESCE(SUM(l.cache_hit_tokens), 0) as cache_hit,
               COALESCE(SUM(l.cache_miss_tokens), 0) as cache_miss,
               COALESCE(SUM(l.completion_tokens), 0) as output_tk
        FROM api_keys k
        LEFT JOIN usage_logs l ON l.api_key_id = k.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (k.key_prefix LIKE ? OR k.name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])
    if status_filter:
        query += " AND k.status = ?"
        params.append(status_filter)
    query += " GROUP BY k.id ORDER BY k.id DESC LIMIT 200"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
