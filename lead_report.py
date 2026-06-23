#!/usr/bin/env python3
"""Lead source report: show order counts by channel."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_lead_stats

def main():
    stats = get_lead_stats()
    print(f"\nLead Source Report")
    print(f"Total orders: {stats['total']}")
    print(f"\n{'Channel':<20} {'Orders':<10}")
    print("-" * 30)
    for ch in stats["channels"]:
        bar = "#" * min(ch["count"], 50)
        print(f"{ch['channel']:<20} {ch['count']:<10} {bar}")
    print()

if __name__ == "__main__":
    main()
