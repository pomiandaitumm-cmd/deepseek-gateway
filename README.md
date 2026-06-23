# DeepSeek API Gateway

**OpenAI-compatible DeepSeek API. Buy a key, start coding — from $1.**

[![Status](https://img.shields.io/badge/status-live-3fb950)](#)
[![HTTPS](https://img.shields.io/badge/SSL-Let%27s_Encrypt-3fb950)](#)
[![PayPal](https://img.shields.io/badge/payment-PayPal-58a6ff)](#)
[![Price](https://img.shields.io/badge/from-%241-3fb950)](#)

```bash
curl https://modelrelayapis.cc/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hello"}]}'
```

---

## What is this?

A **third-party API gateway** that gives you an OpenAI-compatible endpoint for DeepSeek models. You get your own API key with a fixed budget. When the budget runs out, you buy another — no surprise bills, no monthly commitment.

**This is NOT an official DeepSeek service.** It is an independent gateway that forwards requests to DeepSeek's API with managed access, per-key quotas, and usage tracking.

---

## Quick Links

| | | |
|---|---|---|
| **[Pricing & Buy](https://modelrelayapis.cc/pricing.html)** | Plans from $1 | PayPal checkout |
| **[Dashboard](https://modelrelayapis.cc/dashboard.html)** | Check your usage | Real-time budget tracking |
| **[Docs](https://modelrelayapis.cc/docs.html)** | Setup guide | Python, curl, SillyTavern |
| **[API Reference](https://modelrelayapis.cc/api-docs.html)** | Endpoints | Models, errors, rate limits |
| **[Order Status](https://modelrelayapis.cc/order.html)** | Find your key | Look up by Order ID + email |

---

## Pricing

| Plan | Price | API Budget | Model | RPM |
|---|---|---|---|---|
| Trial | $1.00 | $0.70 | deepseek-v4-flash | 30 |
| Starter | $3.00 | $2.30 | deepseek-v4-flash | 30 |
| Standard | $6.00 | $4.80 | deepseek-v4-flash | 60 |
| Pro | $6.00 | $3.80 | flash + pro | 30 |

**Budget-based billing:** Each request deducts from your balance based on real DeepSeek token pricing — input, cache-hit, and output tokens are priced differently. Cache hits can be **10x cheaper**.

[View full pricing ?](https://modelrelayapis.cc/pricing.html)

---

## Quick Start

### Python (OpenAI SDK)

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

### Node.js

```js
const response = await fetch("https://modelrelayapis.cc/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": "Bearer YOUR_KEY",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "deepseek-v4-flash",
    messages: [{ role: "user", content: "Hello!" }],
  }),
});
const data = await response.json();
console.log(data.choices[0].message.content);
```

---

## Features

- **OpenAI-compatible** — Use any OpenAI SDK or client. Just change the base URL.
- **Per-key budget** — Each key has a fixed API budget. No surprise overages.
- **Real-time usage tracking** — Check remaining balance anytime at the [Dashboard](https://modelrelayapis.cc/dashboard.html).
- **PayPal checkout** — Buy a package, pay with PayPal, get your key instantly.
- **Streaming support** — SSE streaming works with all models.
- **Rate limiting** — Per-key RPM limits to keep things fair.
- **Multi-model** — `deepseek-v4-flash` (fast, cheap) and `deepseek-v4-pro` (higher capability).
- **Chinese & English** — Landing page and docs in both languages.

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Health check |
| GET | `/v1/models` | Bearer | List available models |
| POST | `/v1/chat/completions` | Bearer | Chat completions (streaming supported) |
| GET | `/v1/key/usage` | Bearer | Your key's usage and remaining budget |

[Full API docs ?](https://modelrelayapis.cc/api-docs.html)

---

## SillyTavern Setup

SillyTavern works with this gateway out of the box:

1. API type: **OpenAI Compatible**
2. Base URL: `https://modelrelayapis.cc/v1`
3. API Key: your `sk-gateway-...` key
4. Model: `deepseek-v4-flash`

[Step-by-step guide ?](https://modelrelayapis.cc/sillytavern-deepseek-setup.html)

---

## FAQ

**Is this the official DeepSeek API?**
No. This is an independent third-party gateway. We forward requests to DeepSeek's API and add managed access, quotas, and tracking on top.

**How is my budget deducted?**
Each request is priced based on real DeepSeek token costs: input tokens, cache-hit tokens (much cheaper), and output tokens. You can see the breakdown in your [Dashboard](https://modelrelayapis.cc/dashboard.html).

**What happens when my budget runs out?**
Your key returns a `402` error. Just buy a new package — there is no subscription or auto-charge.

**Can I use this with any OpenAI client?**
Yes. Anything that talks to OpenAI's API works: Python SDK, Node.js, LangChain, LobeChat, SillyTavern, Dify, and more.

**How do I get a key?**
Go to [Pricing](https://modelrelayapis.cc/pricing.html), pick a plan, pay with PayPal, and your key is shown instantly.

---

## Deployment (self-host)

If you want to run your own instance:

```bash
cd /opt/deepseek-gateway
docker compose up -d --build
```

Admin scripts:

```bash
# Create a key
docker compose exec deepseek-gateway python create_key.py --name "user" --token-quota 100000

# View usage
docker compose exec deepseek-gateway python usage_report.py

# View orders
docker compose exec deepseek-gateway python order_report.py
```

---

## Important

- **This is NOT an official DeepSeek service.** It is an independent third-party gateway.
- Never share your `DEEPSEEK_API_KEY` (stored in `.env` on your server).
- Never commit `.env`, `db.sqlite3`, or `backups/` to version control.
- Customer keys use the `sk-gateway-` prefix — these are safe to share with customers.
- Budget-based billing: you pay for API budget, not raw tokens. Deductions are calculated per DeepSeek's official pricing.
