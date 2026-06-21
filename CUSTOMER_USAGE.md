# DeepSeek API Gateway - Usage Guide

Base URL: http://65.49.201.211/v1
Model: deepseek-v4-flash
Rate Limit: 30/min
API Key: Provided separately by admin (starts with sk-gateway-)

## curl

curl http://65.49.201.211/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hello"}],"max_tokens":500}'

## Python

from openai import OpenAI
client = OpenAI(base_url="http://65.49.201.211/v1", api_key="YOUR_KEY")
r = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role":"user","content":"Hello"}],
    max_tokens=500,
)
print(r.choices[0].message.content)

## Notes
Each request consumes token quota. Contact admin when quota runs out. Do not share API Key.