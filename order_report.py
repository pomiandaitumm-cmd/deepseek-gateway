#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, list_orders

def main():
    init_db()
    orders = list_orders()
    if not orders:
        print("No orders.")
        return
    header = f"{'ID':<5} {'Status':<10} {'Paid':<6} {'Email':<28} {'Package':<10} {'Quota':<10} {'Key Prefix':<18} {'Created'}"
    print()
    print(header)
    print("-" * 130)
    for o in orders:
        kp = o.get("key_prefix") or "-"
        ps = o.get("payment_status") or "unpaid"
        print(f"{o['id']:<5} {o['status']:<10} {ps:<6} {o['email']:<28} {o['package_name']:<10} {str(o['token_quota']):<10} {kp:<18} {o['created_at']}")
    print()

if __name__ == "__main__":
    main()