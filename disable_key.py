#!/usr/bin/env python3
""""Disable an API key by prefix.""""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, get_db, now_utc


def main():
    parser = argparse.ArgumentParser(description="Disable an API key by prefix")
    parser.add_argument("--prefix", required=True, help="Key prefix (e.g. sk-gateway-xxxx)")
    args = parser.parse_args()

    init_db()

    conn = get_db()
    row = conn.execute(
        "SELECT id, key_prefix, name, status FROM api_keys WHERE key_prefix = ?",
        (args.prefix,)
    ).fetchone()

    if row is None:
        print(f"Error: No key found with prefix '{args.prefix}'")
        conn.close()
        sys.exit(1)

    if row["status"] == "disabled":
        print(f"Key '{args.prefix}' (name: {row['name']}) is already disabled.")
        conn.close()
        sys.exit(0)

    conn.execute(
        "UPDATE api_keys SET status = 'disabled' WHERE key_prefix = ?",
        (args.prefix,)
    )
    conn.commit()
    conn.close()

    print(f"Key '{args.prefix}' (name: {row['name']}) has been disabled.")


if __name__ == "__main__":
    main()