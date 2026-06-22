#!/usr/bin/env python3
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, approve_order

def main():
    p = argparse.ArgumentParser(description="Approve an order and auto-generate API key")
    p.add_argument("--order-id", type=int, required=True, help="Order ID to approve")
    args = p.parse_args()
    init_db()
    result, err = approve_order(args.order_id)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)
    print("=" * 60)
    print("  Order Approved -- API Key Generated!")
    print("=" * 60)
    print(f"")
    print(f"  Order ID:     {result['order_id']}")
    print(f"  Status:       {result['status']}")
    print(f"  Key Name:     {result['name']}")
    print(f"  Key Prefix:   {result['key_prefix']}")
    print(f"  Token Quota:  {result['token_quota']}")
    print(f"  Rate Limit:   {result['rate_limit']}/min")
    print(f"")
    print(f"  FULL KEY (save now -- never shown again!):")
    print(f"  {result['full_key']}")
    print(f"")
    print("=" * 60)

if __name__ == "__main__":
    main()
