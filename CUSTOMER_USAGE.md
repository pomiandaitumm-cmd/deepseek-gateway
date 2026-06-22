# DeepSeek API Gateway — Usage Guide

> **Status: Invite-Only Alpha**
>
> This is an independent, invite-only API gateway. It is NOT an official DeepSeek service.
> Domain and HTTPS are pending. Do not share your API key.

---

## Connection Info

| Item | Value |
|------|-------|
| Base URL | `http://65.49.201.211/v1` |
| Model | `deepseek-v4-flash` |
| Rate Limit | 30 requests per minute |
| Auth | `Bearer` token (provided by admin) |
| Format | OpenAI-compatible |

---

## Quick Test

```bash
curl http://65.49.201.211/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

---

## Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://65.49.201.211/v1",
    api_key="YOUR_KEY",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=500,
)

print(response.choices[0].message.content)
```

---

## JavaScript / Node.js

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://65.49.201.211/v1",
  apiKey: "YOUR_KEY",
});

const response = await client.chat.completions.create({
  model: "deepseek-v4-flash",
  messages: [{ role: "user", content: "Hello" }],
  max_tokens: 500,
});

console.log(response.choices[0].message.content);
```

---

## Streaming

Add `"stream": true` to your request. Works with both Python and JavaScript SDKs — the gateway passes SSE chunks through.

---

## Error Codes

| Code | Meaning | What to Do |
|------|---------|------------|
| 401 | Invalid or missing API key | Check your key, contact admin |
| 402 | Token quota exceeded | Contact admin to top up |
| 403 | Key disabled | Contact admin |
| 429 | Rate limit hit | Wait and retry (30 req/min) |

---

## Notes

- Each request consumes from your token quota
- Quota is measured in `total_tokens` (input + output)
- Contact admin when your quota runs low
- Do not share your API key with anyone
- This is an invite-only alpha — domain and HTTPS are pending
