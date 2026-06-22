#!/usr/bin/env python3
"""Mark an order as paid (manual payment confirmation)."""

import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, mark_order_paid

def main():
    p = argparse.ArgumentParser(description="Mark an order as paid")
    p.add_argument("--order-id", type=int, required=True, help="Order ID to mark as paid")
    p.add_argument("--note", default="manual confirmed", help="Payment note")
    args = p.parse_args()
    init_db()
    result, err = mark_order_paid(args.order_id, args.note)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)
    print(f"Order #{result['order_id']} marked as PAID")
    print(f"  Status:   {result['status']}")
    print(f"  Payment:  {result['payment_status']}")
    print(f"  Email:    {result['email']}")
    print(f"  Package:  {result['package']}")
    print(f"  Note:     {result['note']}")
    print()
    print("Next: approve_order.py --order-id", result["order_id"])

if __name__ == "__main__":
    main()