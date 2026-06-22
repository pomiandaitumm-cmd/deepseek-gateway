#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, get_db

def main():
    init_db()
    conn = get_db()
    rows = conn.execute('''
        SELECT c.*, COUNT(o.id) as order_count,
           GROUP_CONCAT(o.status || ':' || p.name || ':' || COALESCE(o.key_prefix,'-'), ' | ') as orders_info
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.id
        LEFT JOIN packages p ON p.id = o.package_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    ''').fetchall()
    conn.close()
    if not rows:
        print('No customers.')
        return
    header = f"{'ID':<5} {'Email':<30} {'Contact':<25} {'Orders':<4} {'Details'}"
    print()
    print(header)
    print('-' * 140)
    for r in rows:
        print(f"{r['id']:<5} {r['email']:<30} {r['telegram_or_discord']:<25} {r['order_count']:<4} {r['orders_info'] or '-'}")
    print()

if __name__ == '__main__':
    main()
