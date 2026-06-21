#!/usr/bin/env python3
import argparse, secrets, string, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, get_db, hash_key, now_utc

def gen():
    a = string.ascii_letters + string.digits
    return "sk-gateway-" + ''.join(secrets.choice(a) for _ in range(48))

def main():
    p = argparse.ArgumentParser(description="Create API key")
    p.add_argument("--name", required=True)
    p.add_argument("--rate-limit", type=int, default=60)
    p.add_argument("--token-quota", type=int, default=10000)
    args = p.parse_args()
    init_db()
    fk = gen(); kh = hash_key(fk); kp = fk[:16]
    conn = get_db()
    conn.execute("INSERT INTO api_keys (key_hash,key_prefix,name,status,rate_limit_per_minute,token_quota_total,created_at) VALUES (?,?,?,'active',?,?,?)", (kh,kp,args.name,args.rate_limit,args.token_quota,now_utc()))
    conn.commit(); conn.close()
    print("="*60); print("  API Key created!"); print("="*60)
    print(f"\n  Name:        {args.name}")
    print(f"  Prefix:      {kp}")
    print(f"  Rate limit:  {args.rate_limit}/min")
    print(f"  Token quota: {args.token_quota} tokens")
    print(f"\n  FULL KEY (save now -- never shown again!):\n  {fk}\n"); print("="*60)

if __name__ == "__main__": main()