# expire_orders.py — Expire orders past their expires_at time
# Usage: python expire_orders.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, expire_stale_orders

def main():
    init_db()
    count = expire_stale_orders()
    if count > 0:
        print(f"Expired {count} stale order(s)")
    else:
        print("No orders to expire")

if __name__ == "__main__":
    main()
