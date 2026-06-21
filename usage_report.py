#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, get_db

def main():
    init_db(); conn = get_db()
    rows = conn.execute("""
        SELECT k.key_prefix, k.name, k.status, k.token_quota_total, k.token_quota_used, k.last_used_at,
               COUNT(l.id) AS reqs, COALESCE(SUM(l.total_tokens),0) AS ttok
        FROM api_keys k LEFT JOIN usage_logs l ON l.api_key_id=k.id
        GROUP BY k.id ORDER BY k.created_at DESC
    """).fetchall()
    if not rows: print("No keys."); conn.close(); return
    print(f"\n{'Prefix':<20} {'Name':<12} {'Status':<8} {'Reqs':<6} {'Total Tok':<10} {'Used Quota':<12} {'Total Quota':<12} {'Remaining':<12} {'Last Used':<20}")
    print("-"*115)
    for r in rows:
        qt = r["token_quota_total"] or 0; qu = r["token_quota_used"] or 0; rem = qt - qu
        qts = str(qt) if qt > 0 else "unlimited"; rems = str(rem) if qt > 0 else "unlimited"
        print(f"{r['key_prefix']:<20} {r['name']:<12} {r['status']:<8} {r['reqs']:<6} {r['ttok']:<10} {qu:<12} {qts:<12} {rems:<12} {r['last_used_at'] or 'N/A':<20}")
    print(); conn.close()

if __name__ == "__main__": main()