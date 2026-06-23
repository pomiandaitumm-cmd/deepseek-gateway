# payment_watcher.py — Daemon: polls TronGrid for TRC20 USDT transfers, matches pending orders, auto-approves
# Usage: python payment_watcher.py [--dry-run] [--interval SECONDS]

import os, sys, time, json, random, urllib.request, urllib.error, hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import (init_db, get_pending_orders, check_payment_match,
                          process_payment, expire_stale_orders, PAYMENT_ADDRESS,
                          PAYMENT_NETWORK, PAYMENT_TOKEN, TRONGRID_API_BASE,
                          PAYMENT_POLL_INTERVAL, ORDER_EXPIRY_MINUTES)

DRY_RUN = "--dry-run" in sys.argv
INTERVAL = PAYMENT_POLL_INTERVAL

# Override interval from CLI
for i, arg in enumerate(sys.argv):
    if arg == "--interval" and i + 1 < len(sys.argv):
        try:
            INTERVAL = int(sys.argv[i + 1])
        except ValueError:
            pass

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)

def query_trc20_transfers(address):
    """Query TRC20 USDT transfers for a given address via TronGrid API."""
    if DRY_RUN:
        return []
    if not address or address.startswith("PLACEHOLDER"):
        return []
    # TRC20 USDT contract: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
    contract = os.environ.get("USDT_CONTRACT", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
    url = (f"{TRONGRID_API_BASE}/v1/accounts/{address}/transactions/trc20"
           f"?contract_address={contract}"
           f"&only_confirmed=true&only_to=true&limit=20&min_timestamp={int(time.time()) - 3600}")
    try:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/json")
        # TronGrid API key (optional but recommended)
        api_key = os.environ.get("TRONGRID_API_KEY", "")
        if api_key:
            req.add_header("TRON-PRO-API-KEY", api_key)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", [])
    except Exception as e:
        log(f"TronGrid query error: {e}")
        return []

def match_amount(expected, actual):
    """Check if actual matches expected within tolerance.
    TronGrid returns amount as integer (value * 10^decimals)."""
    # USDT TRC20 has 6 decimals normally; TronGrid returns raw int
    # But sometimes returns as-is. Handle both.
    if actual > 1000000:
        actual = actual / 1_000_000  # convert from raw int
    return check_payment_match(expected, actual)

def run_once():
    """Single poll cycle."""
    init_db()

    # First, expire stale orders
    count = expire_stale_orders()
    if count > 0:
        log(f"Expired {count} stale orders")

    # Get pending orders
    orders = get_pending_orders()
    if not orders:
        log(f"No pending orders to check ({'DRY RUN' if DRY_RUN else 'live'})")
        return 0

    log(f"Checking {len(orders)} pending orders ({'DRY RUN' if DRY_RUN else 'live'})")
    matched = 0

    for order in orders:
        oid = order["id"]
        expected = order.get("expected_amount", 0)
        if not expected or expected <= 0:
            continue

        if DRY_RUN:
            # Simulate payment for the first pending order
            if matched == 0:
                tx_hash = f"DRYRUN_{oid}_{int(time.time())}_{random.randint(1000, 9999)}"
                log(f"  DRY RUN: simulating tx {tx_hash} for order #{oid} amount={expected}")
                result, err = process_payment(
                    oid, tx_hash,
                    from_address="DRYRUN_SENDER",
                    to_address=PAYMENT_ADDRESS,
                    amount=expected,
                    raw_json=json.dumps({"dry_run": True}),
                )
                if err:
                    log(f"  ERROR: {err}")
                else:
                    log(f"  APPROVED order #{oid} key={result.get('key_prefix', '???')} tx={tx_hash}")
                    matched += 1
        else:
            # Query real TronGrid
            txs = query_trc20_transfers(PAYMENT_ADDRESS)
            for tx in txs:
                tx_hash = tx.get("transaction_id", "")
                tx_amount = float(tx.get("value", 0))
                from_addr = tx.get("from", "")
                to_addr = tx.get("to", "")

                if not tx_hash:
                    continue
                if not match_amount(expected, tx_amount):
                    continue

                result, err = process_payment(
                    oid, tx_hash,
                    from_address=from_addr,
                    to_address=to_addr,
                    amount=tx_amount,
                    raw_json=json.dumps(tx),
                )
                if err:
                    if "already processed" in str(err).lower():
                        continue
                    log(f"  ERROR order #{oid}: {err}")
                else:
                    log(f"  MATCHED order #{oid} tx={tx_hash[:16]}... amount={tx_amount}")
                    log(f"  APPROVED key={result.get('key_prefix', '???')}")
                    matched += 1
                    break

    return matched

def main():
    if "--once" in sys.argv:
        log("Running single check...")
        run_once()
        return

    log(f"Starting payment_watcher {'(DRY RUN)' if DRY_RUN else ''} interval={INTERVAL}s")
    while True:
        try:
            run_once()
        except Exception as e:
            log(f"Cycle error: {e}")
        log(f"Sleeping {INTERVAL}s...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
