# DeepSeek API Gateway -- Customer Usage Guide

**Base URL:** http://modelrelayapis.cc/v1
**Model:** deepseek-v4-flash (also available: deepseek-v4-pro)
**Rate Limit:** Configurable per key (default 30 requests/min)
**API Key:** Provided by admin (starts with sk-gateway-)

## Curl Example

```bash
curl http://modelrelayapis.cc/v1/chat/completions   -H "Authorization: Bearer YOUR_KEY"   -H "Content-Type: application/json"   -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hello"}],"max_tokens":500}'
```

## Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(base_url="http://modelrelayapis.cc/v1", api_key="YOUR_KEY")

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role":"user","content":"Hello!"}],
    max_tokens=500,
)
print(response.choices[0].message.content)
```

## Check Your Usage

Visit http://modelrelayapis.cc/dashboard.html and enter your API key.

Or via API:
```bash
curl http://modelrelayapis.cc/v1/key/usage   -H "Authorization: Bearer YOUR_KEY"
```

## Notes

- This is an **invite-only alpha** gateway (third-party, not official DeepSeek).
- **Domain and HTTPS are pending.**
- **Never share your API key.** Each key is tied to your quota.
- When your token quota runs out, you will receive HTTP 402.
- If you exceed the rate limit, you will receive HTTP 429.
- All usage is tracked per request. No prompt or completion content is saved.
