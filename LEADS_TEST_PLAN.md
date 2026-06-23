# 48-Hour Lead Test Plan

> Internal planning doc. Do NOT share with testers.

## Objective

Find 3 real developers willing to try the DeepSeek Gateway API using test tokens, and gauge whether any would convert to paying customers.

## What We''re Testing

1. **Interest** — Do developers respond to cold outreach about a cheaper DeepSeek API gateway?
2. **Activation** — If given free test tokens, do they actually make API calls?
3. **Retention** — Do they come back after the first call?
4. **Conversion signal** — Do they ask about pricing, quotas, or how to pay?

## Offer to Testers

- **100,000 test tokens** per person
- Base URL: `https://modelrelayapis.cc/v1`
- Model: `deepseek-v4-flash`
- Rate limit: 30 req/min
- No payment required
- No commitment

## What We Are NOT

- NOT an official DeepSeek service
- NOT an official reseller or partner
- NOT DeepSeek itself
- This is an independent, invite-only gateway

## Test Duration

48 hours from first key creation. Extend if tester is active and asking questions.

## Channels

| Channel | Target | Approach |
|---------|--------|----------|
| Telegram groups (AI/dev) | 2 testers | DM after helpful comment |
| Discord (AI/coding servers) | 1 tester | DM after answering a question |
| Reddit r/LocalLLaMA, r/selfhosted | 1 tester | Comment reply, not new post |
| WeChat /熟人 | 1 backup | Casual chat, not sales pitch |

## Observation Checklist

For each tester, track:

- [ ] Did they accept the free key?
- [ ] Did they make at least 1 API call?
- [ ] How many calls in first 24h? (`usage_report.py`)
- [ ] How many tokens consumed?
- [ ] Did they ask about pricing?
- [ ] Did they ask about larger quotas?
- [ ] Did they report any bugs or issues?
- [ ] Did they ask for more tokens after running out?
- [ ] Would they recommend to others?

## Rules

- Never claim to be DeepSeek official
- Never share our DeepSeek API key
- Never share other testers'' keys
- Never promise unlimited tokens
- Never promise a specific launch date
- If someone asks "are you official" — answer honestly: "No, this is an independent gateway"

## Success Criteria

A tester is "warm" if:
- Made 5+ API calls across 24h
- Asked about pricing OR larger quotas
- Responded positively to follow-up

A tester is "cold" if:
- Never used the key at all
- Used once and never came back
- Complained about speed/quality and left

Goal: at least **1 warm lead** out of 3.

## After 48 Hours

1. Run `usage_report.py` and screenshot
2. Disable unused test keys
3. Write brief feedback summary
4. Decide: proceed to paid beta, or adjust offering
