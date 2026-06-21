import sqlite3
import hashlib
import os
from datetime import datetime, timezone

_default_docker = "/app/data/db.sqlite3"
_default_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db.sqlite3")
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
    """)
    conn.commit()
    _migrate_add(conn, "api_keys", "token_quota_total", "INTEGER NOT NULL DEFAULT 10000")
    _migrate_add(conn, "api_keys", "token_quota_used", "INTEGER NOT NULL DEFAULT 0")
    _migrate_add(conn, "api_keys", "request_quota_total", "INTEGER")
    _migrate_add(conn, "api_keys", "request_quota_used", "INTEGER DEFAULT 0")
    conn.close()

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