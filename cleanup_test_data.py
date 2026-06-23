#!/usr/bin/env python3
"""Clean up test/demo data from the gateway database.
Usage:
  python cleanup_test_data.py           # dry-run: show what would be deleted
  python cleanup_test_data.py --yes     # actually delete
"""

import sqlite3, sys, argparse

DB = "data/db.sqlite3"

# Rules for identifying test data
TEST_EMAIL_PATTERNS = [
    "test@", "test-", "-test@", "e2e-", "demo@", "fake@",
    "sb-",  # PayPal sandbox buyer
    "personal.example.com",
    "example.com",
    "budget-test@",
    "quota-test",
    "pro-model-test",
    "legacy-test",
    "paypal-test",
    "pkg-test",
    "test-v07",
    "v06-trial",
    "v06-pro",
    "real-user-1",
    "first-user",
    "public-test",
    "alpha-user-1",
]

TEST_KEY_NAMES = [
    "quota-test", "public-test", "real-user-1", "first-user",
    "alpha-user-1", "budget-test@test.com", "legacy-test@example.com",
    "test-public-order@e2e.test",
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Actually delete (default: dry-run)")
    args = parser.parse_args()

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    # Find test orders
    orders_to_delete = []
    all_orders = db.execute("""
        SELECT o.id, o.issued_key, o.key_prefix, o.status, o.payment_status,
               o.payment_provider, c.email, p.name as pkg_name, o.created_at
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        LEFT JOIN packages p ON o.package_id = p.id
        ORDER BY o.id
    """).fetchall()

    for o in all_orders:
        email = (o["email"] or "").lower()
        is_test = False
        reason = ""

        # Match test patterns
        for pat in TEST_EMAIL_PATTERNS:
            if pat.lower() in email:
                is_test = True
                reason = f"email matches '{pat}'"
                break

        # Also match by key name
        if not is_test and o["key_prefix"]:
            key_row = db.execute("SELECT name FROM api_keys WHERE key_prefix = ?", (o["key_prefix"],)).fetchone()
            if key_row:
                kn = (key_row["name"] or "").lower()
                for tn in TEST_KEY_NAMES:
                    if tn.lower() in kn:
                        is_test = True
                        reason = f"key name matches '{tn}'"
                        break

        if is_test:
            orders_to_delete.append((o, reason))

    # Find test keys not linked to orders
    keys_to_delete = []
    all_keys = db.execute("""
        SELECT k.key_prefix, k.name, k.status, k.upstream_cost_used
        FROM api_keys k
        WHERE k.key_prefix NOT IN (SELECT key_prefix FROM orders WHERE key_prefix IS NOT NULL)
        ORDER BY k.created_at
    """).fetchall()

    for k in all_keys:
        name = (k["name"] or "").lower()
        for pat in TEST_EMAIL_PATTERNS:
            if pat.lower() in name:
                keys_to_delete.append((k, f"name matches '{pat}'"))
                break

    # Also include disabled keys that match known test prefixes
    OLD_TEST_PREFIXES = [
        "sk-gateway-LtPHi", "sk-gateway-0HUvs", "sk-gateway-uTraB",
        "sk-gateway-SSWVR", "sk-gateway-PcCuA",
    ]
    for k in all_keys:
        if k["key_prefix"] in OLD_TEST_PREFIXES:
            already = any(k2[0]["key_prefix"] == k["key_prefix"] for k2 in keys_to_delete)
            if not already:
                keys_to_delete.append((k, "known old test prefix"))

    # PRINT
    print("=" * 70)
    print(f"MODE: {'DRY-RUN (no changes)' if not args.yes else 'LIVE DELETE'}")
    print("=" * 70)

    print(f"\n?? Orders to delete: {len(orders_to_delete)}")
    print("-" * 70)
    print(f"{'ID':<5} {'Email':<35} {'Plan':<12} {'Pay':<8} {'Key Prefix':<20} {'Reason'}")
    print("-" * 70)
    for o, reason in orders_to_delete:
        kp = (o["key_prefix"] or "")[:20]
        em = (o["email"] or "")[:33]
        pl = (o["pkg_name"] or "")[:10]
        ps = (o["payment_status"] or "")[:6]
        print(f"{o['id']:<5} {em:<35} {pl:<12} {ps:<8} {kp:<20} {reason}")

    print(f"\n?? Keys to delete (no order): {len(keys_to_delete)}")
    print("-" * 70)
    for k, reason in keys_to_delete:
        print(f"  {k['key_prefix']:<22} {k['name']:<30} {k['status']:<12} {reason}")

    # Also check for customers to delete
    test_emails = db.execute("""
        SELECT c.id, c.email FROM customers c
        WHERE c.id IN (SELECT customer_id FROM orders WHERE id IN ({}))
    """.format(",".join(str(o[0]["id"]) for o in orders_to_delete))).fetchall() if orders_to_delete else []

    print(f"\n?? Customers to delete: {len(test_emails)}")

    if not args.yes:
        print("\n??  DRY-RUN complete. Run with --yes to actually delete.")
    else:
        # DELETE
        if orders_to_delete:
            order_ids = [str(o[0]["id"]) for o in orders_to_delete]
            # Delete payments
            db.execute(f"DELETE FROM payments WHERE order_id IN ({','.join(order_ids)})")
            # Delete usage logs
            db.execute(f"DELETE FROM usage_logs WHERE key_prefix IN (SELECT key_prefix FROM orders WHERE id IN ({','.join(order_ids)}))")
            # Delete orders
            db.execute(f"DELETE FROM orders WHERE id IN ({','.join(order_ids)})")

        if keys_to_delete:
            key_prefixes = ["'" + k[0]["key_prefix"] + "'" for k in keys_to_delete]
            db.execute(f"DELETE FROM usage_logs WHERE key_prefix IN ({','.join(key_prefixes)})")
            db.execute(f"DELETE FROM api_keys WHERE key_prefix IN ({','.join(key_prefixes)})")

        if test_emails:
            cust_ids = [str(c["id"]) for c in test_emails]
            db.execute(f"DELETE FROM customers WHERE id IN ({','.join(cust_ids)})")

        db.commit()
        remaining_orders = db.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
        remaining_keys = db.execute("SELECT COUNT(*) as c FROM api_keys").fetchone()["c"]
        print(f"\n? Deleted. Remaining: {remaining_orders} orders, {remaining_keys} keys.")

    db.close()

if __name__ == "__main__":
    main()
