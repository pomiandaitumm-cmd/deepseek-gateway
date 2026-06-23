# DeepSeek API Gateway

OpenAI-compatible API Gateway for DeepSeek models. Managed access with per-key quotas, rate limiting, and usage tracking.

**Status:** Alpha ? Invite Only
**Base URL:** https://modelrelayapis.cc/v1
**Domain + HTTPS:** Pending

## Features

- **OpenAI-compatible endpoint** ? Use the standard `openai` Python SDK
- **Per-key token quotas** ? Clear tracking, no surprise bills
- **Rate limiting** ? Configurable per-key requests/minute
- **Streaming support** ? SSE streaming works out of the box
- **Usage dashboard** ? Customers can check usage at `/dashboard.html`
- **Apply page** ? Self-service applications at `/apply.html`
- **Multi-model** ? `deepseek-v4-flash`, `deepseek-v4-pro`

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | Landing page (EN/CN) |
| Dashboard | `/dashboard.html` | Check API key usage |
| Pricing | `/pricing.html` | Plans and pricing |
| Apply | `/apply.html` | Apply for API access |
| SillyTavern Setup | `/sillytavern-deepseek-setup.html` | SillyTavern guide |
| Compare Options | `/openrouter-vs-direct-deepseek.html` | Comparison guide |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/v1/models` | Bearer | List models |
| POST | `/v1/chat/completions` | Bearer | Chat completions |
| GET | `/v1/key/usage` | Bearer | Key usage stats |
| GET | `/api/packages` | None | List packages |
| POST | `/api/apply` | None | Submit application |

## Quick Start (Python)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://modelrelayapis.cc/v1",
    api_key="sk-gateway-YOUR-KEY",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

## Admin Scripts

```bash
# Create a key
docker compose exec deepseek-gateway python create_key.py --name "user" --token-quota 100000

# Disable a key
docker compose exec deepseek-gateway python disable_key.py --prefix sk-gateway-xxxx

# Add quota
docker compose exec deepseek-gateway python add_quota.py --prefix sk-gateway-xxxx --tokens 50000

# Set quota
docker compose exec deepseek-gateway python set_quota.py --prefix sk-gateway-xxxx --tokens 100000

# View usage
docker compose exec deepseek-gateway python usage_report.py

# View orders
docker compose exec deepseek-gateway python order_report.py

# View customers
docker compose exec deepseek-gateway python customer_report.py

# Approve an order (generates API key)
docker compose exec deepseek-gateway python approve_order.py --order-id 1
```

## Deployment

```bash
# On VPS
cd /opt/deepseek-gateway
docker compose up -d --build
```

## Important

**This is NOT an official DeepSeek service.** It is a third-party managed gateway that forwards requests to DeepSeek's API.

- Never share your `DEEPSEEK_API_KEY` (in `.env`)
- Never commit `.env`, `db.sqlite3`, or `backups/`
- Customer keys use `sk-gateway-` prefix
- Quota is based on DeepSeek's `usage.total_tokens`
