# Test User Checklist — 48h Lead Test

> Quick reference for managing test users during the 48-hour test period.

---

## 1. Create a Tester Key

```bash
cd /opt/deepseek-gateway
docker compose exec deepseek-gateway python create_key.py \
  --name "tester-<name>" \
  --token-quota 100000
```

Example:
```bash
docker compose exec deepseek-gateway python create_key.py --name "tester-alex" --token-quota 100000
```

**Save the full key immediately** — it only appears once.

---

## 2. Record Tester Info

Keep a simple log (text file / Notion / spreadsheet):

| Field | Example |
|-------|---------|
| Name | Alex |
| Contact | Telegram @alex_dev |
| Channel | Reddit r/LocalLLaMA |
| Key prefix | sk-gateway-AbCd... |
| Date given | 2026-06-22 |
| Token quota | 100,000 |
| Notes | Uses Python SDK, building a chatbot |

---

## 3. Send to Tester

Template message:
```
Here's your test key:

Base URL: http://modelrelayapis.cc/v1
API Key: sk-gateway-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Model: deepseek-v4-flash
Rate Limit: 30 req/min
Test Tokens: 100,000

Usage guide: http://modelrelayapis.cc/
(Customer doc also at the /v1 base path)

This is an invite-only alpha. Domain + HTTPS coming soon.
Let me know if you hit any issues!
```

---

## 4. Monitor Usage

```bash
cd /opt/deepseek-gateway
docker compose exec deepseek-gateway python usage_report.py
```

Check daily:
- [ ] Has the tester made any calls?
- [ ] How many tokens used / remaining?
- [ ] Any error patterns in logs? (`docker compose logs --tail 50`)

---

## 5. Add More Tokens (If Needed)

```bash
docker compose exec deepseek-gateway python add_quota.py \
  --prefix sk-gateway-xxxx --tokens 50000
```

Only add tokens if tester is actively using the key and providing feedback.

---

## 6. Disable Test Key

```bash
docker compose exec deepseek-gateway python disable_key.py \
  --prefix sk-gateway-xxxx
```

Disable when:
- 48-hour test period ends
- Tester is unresponsive
- Tester abused the key (unlikely at this scale, but watch for it)

---

## 7. After Test — Summary

For each tester, write 2-3 lines:
- Did they use the key? How much?
- Did they ask about pricing?
- Would they pay? If not, why?
- Any bugs or complaints?

Example:
```
tester-alex: Used 87k/100k tokens. Asked about pricing for 1M tokens.
Said he'd pay ~$5/mo for 1M tokens. No bugs reported. Warm lead.
```

---

## 8. Cleanup After Test

```bash
# 1. Screenshot usage_report
docker compose exec deepseek-gateway python usage_report.py

# 2. Disable all test keys
docker compose exec deepseek-gateway python disable_key.py --prefix sk-gateway-xxxx
docker compose exec deepseek-gateway python disable_key.py --prefix sk-gateway-yyyy

# 3. Backup database
cp data/db.sqlite3 backups/db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)

# 4. Summarize findings → report back
```
