# check_payment_once.py — Single-run payment check for testing
# Usage: python check_payment_once.py [--dry-run] [--order-id N] [--tx-hash MOCK_HASH]

import os, sys, json, random, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import (init_db, get_pending_orders, process_payment,
                          expire_stale_orders, PAYMENT_ADDRESS)

def main():
    dry_run = "--dry-run" in sys.argv
    target_order_id = None
    mock_tx_hash = None

    for i, arg in enumerate(sys.argv):
        if arg == "--order-id" and i + 1 < len(sys.argv):
            target_order_id = int(sys.argv[i + 1])
        if arg == "--tx-hash" and i + 1 < len(sys.argv):
            mock_tx_hash = sys.argv[i + 1]

    init_db()

    # Expire stale first
    cnt = expire_stale_orders()
    if cnt > 0:
        print(f"Expired {cnt} stale orders")

    orders = get_pending_orders()
    if not orders:
        print("No pending orders found.")
        return

    print(f"Found {len(orders)} pending order(s):")

    for o in orders:
        oid = o["id"]
        expected = o.get("expected_amount", 0)
        status = f"order #{oid} plan={o.get('pkg_name', '?')} expected={expected} USDT expires={o.get('expires_at', 'N/A')}"
        print(f"  {status}")

        if target_order_id and oid != target_order_id:
            continue

        if dry_run:
            tx_hash = mock_tx_hash or f"TEST_TX_{oid}_{int(time.time())}_{random.randint(1000,9999)}"
            print(f"  -> DRY RUN: simulating payment tx={tx_hash}")
            result, err = process_payment(
                oid, tx_hash,
                from_address="TEST_SENDER",
                to_address=PAYMENT_ADDRESS,
                amount=expected,
                raw_json=json.dumps({"test": True}),
            )
            if err:
                print(f"  -> ERROR: {err}")
            else:
                print(f"  -> APPROVED! key_prefix={result.get('key_prefix','???')} full_key={result.get('full_key','???')}")
            if target_order_id:
                break
        else:
            print(f"  -> LIVE mode: not implemented without real TRC20 address.")
            print(f"  -> Set PAYMENT_ADDRESS in .env first.")

if __name__ == "__main__":
    main()
