#!/usr/bin/env python3
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, get_db

def main():
    p = argparse.ArgumentParser(description="Set token quota")
    p.add_argument("--prefix", required=True); p.add_argument("--tokens", type=int, required=True)
    args = p.parse_args()
    if args.tokens < 0: print("Error: --tokens >= 0"); sys.exit(1)
    init_db(); conn = get_db()
    row = conn.execute("SELECT id,key_prefix,name,token_quota_total,token_quota_used FROM api_keys WHERE key_prefix=?", (args.prefix,)).fetchone()
    if not row: print(f"Error: no key with prefix {args.prefix!r}"); conn.close(); sys.exit(1)
    ot = row["token_quota_total"] or 0
    conn.execute("UPDATE api_keys SET token_quota_total=? WHERE key_prefix=?", (args.tokens, args.prefix))
    conn.commit(); conn.close()
    print(f"Key {args.prefix!r} ({row['name']})  Old: {ot}  New: {args.tokens}  Used: {row['token_quota_used']}  Remaining: {args.tokens - row['token_quota_used']}")

if __name__ == "__main__": main()