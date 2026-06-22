# Outreach Copy — English + Chinese Notes

> Internal reference. Adapt based on context before sending.

---

## 1. Telegram / Discord DM

**English:**

> Hey! Saw your message about DeepSeek API — I run a small invite-only gateway that gives you API access without needing a Chinese phone number or Alipay.
>
> It''s OpenAI-compatible (just change `base_url`), supports `deepseek-v4-flash`, and I''m giving out 100k free test tokens to a few devs this week.
>
> Interested? Happy to send you a key — no strings attached, just looking for feedback.

**中文注释：**
- 开头用对方说过的话切入，显得你不是群发
- "no strings attached" 降低防备
- 不要一上来就推销，用"找 feedback"的姿态

---

## 2. Reddit Comment Reply

**English:**

> If you just want API access without the hassle of verifying a Chinese phone number, you can try an independent gateway. Some are invite-only right now and offer test tokens to developers.
>
> Base URL is just `http://<ip>/v1`, works with the OpenAI Python SDK — change `base_url` and add your API key, everything else stays the same.
>
> DM me if you want a link to the test program.

**中文注释：**
- Reddit 忌讳硬广，用"some are"第三人称模糊化
- 不提价格、不提自己的项目名
- 留 DM 钩子而不是直接发链接
- 重点：不违反 r/LocalLLaMA 的 self-promo 规则

---

## 3. GitHub README / Issue Reply

**English:**

> For those who want DeepSeek API without phone verification: there are independent API gateways that proxy requests. OpenAI-compatible, just change `base_url`.
>
> Example usage with the Python SDK:
> ```python
> from openai import OpenAI
> client = OpenAI(
>     api_key="your-gateway-key",
>     base_url="http://<gateway-ip>/v1",
> )
> response = client.chat.completions.create(
>     model="deepseek-v4-flash",
>     messages=[{"role": "user", "content": "Hello"}],
> )
> ```
>
> Some gateways offer free test tokens if you reach out. Worth checking.

**中文注释：**
- GitHub 上以"帮助解决技术问题"的姿态出现
- 提供可用的代码示例增加可信度
- 不直接打广告，用"some gateways"模糊化
- 真实帮助对方解决问题，顺便提一嘴

---

## 4. WeChat / Known Developer

**中文原文：**

> 最近搞了个 DeepSeek API 的转接网关，OpenAI 兼容的，直接改 base_url 就能用，不用折腾国内手机号验证。
>
> 现在还在邀请测试阶段，给你 10 万 token 免费试用，帮我测测速度和稳定性？
>
> 就一个 HTTP 接口，Python SDK 直接改 base_url 就行。

**English notes:**
- Keep it casual — this is a friend/acquaintance, not a customer
- Frame as "help me test" not "buy from me"
- No pricing discussion unless they ask
- Goal: get honest technical feedback first, sales conversation later

---

## General Rules for All Channels

1. **Never say "official"** — always "independent gateway"
2. **Never say "unlimited"** — always state the token cap
3. **Never share our DeepSeek key** — users only know their sk-gateway key
4. **Never spam** — one message per person, respect silence
5. **Help first, pitch second** — answer their actual question before mentioning the gateway
6. **If asked about pricing**: "Still finalizing, but roughly $X for Y tokens. Free test tokens available now if you want to try."
7. **If asked about reliability**: "Single VPS right now, working on domain + HTTPS. Good for dev/testing, monitor before production use."
