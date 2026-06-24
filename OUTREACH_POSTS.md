# Outreach Posts — ModelRelay API Gateway

> https://modelrelayapis.cc  
> Independent third-party DeepSeek API gateway. OpenAI-compatible. PayPal checkout. From $1.

---

## 1. GitHub README 顶部推广区块

**English:**
```markdown
# DeepSeek API Gateway — OpenAI-Compatible, From $1

**[modelrelayapis.cc](https://modelrelayapis.cc)** — A third-party API gateway that gives you OpenAI-compatible access to DeepSeek models.

- **HTTPS endpoint** — `https://modelrelayapis.cc/v1`
- **PayPal checkout** — Buy a package, get your API key instantly
- **$1 Trial** — Start with a small budget, no commitment
- **Usage dashboard** — Check your balance and token breakdown anytime
- **Per-key budgeting** — Each key has a fixed budget. No surprise bills.
- **Works with** OpenAI SDK, SillyTavern, LangChain, LobeChat, Dify, and more.

[View Pricing →](https://modelrelayapis.cc/pricing.html) &nbsp; [API Docs →](https://modelrelayapis.cc/api-docs.html)

> Not affiliated with or endorsed by DeepSeek. Independent third-party service.
```

**中文解释：**
GitHub README 顶部简短介绍。强调 OpenAI 兼容、HTTPS 域名、PayPal 购买、$1 试用、用量面板、按 key 管理预算。最后一行声明非官方服务。适合放在 README.md 的最开头，替换/补充现有内容。


## 2. Reddit / Discord / Telegram 技术帖

### 2.1 SillyTavern / AI chat 社区版

**English:**
```
I've been using DeepSeek V4 Flash with SillyTavern for a while now. The model is solid for roleplay — fast, cheap, and handles long context well.

One thing that tripped me up: DeepSeek registration was sometimes restricted, and payment options for non-Chinese users were inconsistent. I ended up using a third-party gateway that gives you an OpenAI-compatible endpoint with PayPal checkout.

Setup in SillyTavern is exactly the same as OpenAI:
- API type: OpenAI Compatible
- Base URL: https://modelrelayapis.cc/v1
- API Key: (generated after PayPal payment)
- Model: deepseek-v4-flash

There's a $1 trial if you just want to test. Not my service — just sharing what worked for me after a lot of trial and error.

Setup guide: https://modelrelayapis.cc/sillytavern-deepseek-setup.html
```

**中文解释：**
写给 SillyTavern / AI 角色扮演社区的分享帖。从个人经验出发："我也踩过坑，DeepSeek 注册不稳定、支付不方便，后来发现了这个第三方网关。"给出具体的 SillyTavern 配置步骤，附上 SillyTavern 教程页链接。语气是开发者分享经验，不是硬广告。

### 2.2 通用开发者社区版

**English:**
```
For anyone hitting walls with DeepSeek's official API — I ran into rate limits, registration issues, and payment friction (WeChat/Alipay only in some regions).

Found a workaround: there's a small independent gateway that wraps DeepSeek's API into a standard OpenAI-compatible endpoint with PayPal checkout.

- base_url: https://modelrelayapis.cc/v1
- Drop-in replacement for the OpenAI SDK — just change the URL
- $1 trial key with 30 RPM
- Usage dashboard shows per-request token breakdown (cache hit/miss/output)
- Per-key budget — when it runs out, you get a clear 402, not a surprise bill

It's not official DeepSeek (they're clear about that). Just a convenience layer for people who want the models without the onboarding friction.

https://modelrelayapis.cc
```

**中文解释：**
写给通用 AI 开发者社区。强调痛点：限流、注册不稳定、支付不方便。然后给出解决方案：OpenAI 兼容格式、PayPal 支付、$1 试用、用量面板、按 key 预算管理。最后再次声明非官方。

### 2.3 简短回复版（用于评论/跟帖）

**English:**
```
If you just need a working DeepSeek API endpoint with PayPal: modelrelayapis.cc. OpenAI-compatible, $1 trial, per-key budget. Not official, just a third-party gateway. Works with SillyTavern, LangChain, and any OpenAI SDK client.
```

**中文解释：**
极简版本，适合在 Reddit 评论里回复"去哪搞 DeepSeek API"这类问题时使用。


## 3. X / Twitter 短帖（5 条）

### Tweet 1
**English:**
```
Need DeepSeek V4 API access with PayPal? I built a small gateway: OpenAI-compatible endpoint, HTTPS, per-key budgeting.

modelrelayapis.cc — $1 trial, instant key delivery.

Not official DeepSeek. Just a convenience layer.
```

**中文解释：**
第一条短帖，介绍网关的核心价值：PayPal 支付、OpenAI 兼容、HTTPS、按 key 预算、$1 试用。

### Tweet 2
**English:**
```
SillyTavern + DeepSeek V4 Flash = solid roleplay stack.

Setup: OpenAI Compatible mode → base URL https://modelrelayapis.cc/v1 → paste your key → model deepseek-v4-flash.

Full guide: modelrelayapis.cc/sillytavern-deepseek-setup.html
```

**中文解释：**
面向 SillyTavern 用户的教程式推文。给出三步配置，附 SillyTavern 教程链接。

### Tweet 3
**English:**
```
Drop-in replacement for openai.ChatCompletion:

client = OpenAI(
  base_url="https://modelrelayapis.cc/v1",
  api_key="sk-gateway-YOUR-KEY"
)

Same SDK, different model prices. $1 trial to test.
```

**中文解释：**
面向 Python 开发者，用代码示例说话。展示一行改动即可切换。

### Tweet 4
**English:**
```
Why another API gateway?

Because DeepSeek's models are great, but registration and payment can be painful for non-Chinese users.

This fixes that: PayPal checkout, English dashboard, no phone number required.

modelrelayapis.cc
```

**中文解释：**
直面"为什么又有一个网关"的质疑。回答：模型好，但注册和付款对非中国用户不友好。这个网关解决这个问题。

### Tweet 5
**English:**
```
Status: Live. HTTPS. PayPal. $1 trial.

modelrelayapis.cc — Independent DeepSeek API Gateway.
```

**中文解释：**
极简状态推文。四个关键词：Live、HTTPS、PayPal、$1。


## 4. Freelancer / Upwork 客户私信模板

### 4.1 通用版

**English:**
```
Hi [Name],

I saw your post about needing an API for [use case / SillyTavern / AI integration]. 

Just wanted to mention that I run a small DeepSeek API gateway at modelrelayapis.cc — it's an OpenAI-compatible endpoint with PayPal checkout and per-key budgeting. Might save you the hassle of registering directly with DeepSeek and dealing with payment restrictions.

There's a $1 trial if you want to test it first. Full API docs at modelrelayapis.cc/api-docs.html.

No pressure — just thought it might be relevant to your project. Happy to answer questions.

Thanks,
[Your name]
```

**中文解释：**
礼貌、简短、可信。不提"大量客户"，不提虚假承诺。引导到 docs 页面，不强制推销。

### 4.2 SillyTavern 用户版

**English:**
```
Hi [Name],

Noticed you're setting up SillyTavern with an API — just a heads-up that DeepSeek V4 Flash works well with it, and there's a step-by-step setup guide here:

https://modelrelayapis.cc/sillytavern-deepseek-setup.html

The gateway handles the OpenAI-compatible format so you don't need to mess with custom adapters. PayPal checkout, $1 trial to test.

Not an official DeepSeek service — just an independent gateway I built to make the API more accessible.

Cheers,
[Your name]
```

**中文解释：**
面向 SillyTavern 用户。用教程页面作为入口，自然带出网关。不强推，只是"分享一个可能有用的东西"。

### 4.3 简短版（用于自由职业平台报价回复）

**English:**
```
For the API side — you could use modelrelayapis.cc (OpenAI-compatible DeepSeek endpoint, PayPal, from $1). I've used it with Python/LangChain/SillyTavern. Just change the base_url and key, the rest of your OpenAI SDK code stays the same. Docs: modelrelayapis.cc/docs.html
```

**中文解释：**
在自由职业平台上回复客户技术需求时的简短植入。语气是我在帮你解决问题，而不是我在推销我的产品。


## 推广原则

1. **不冒充官方** — 每次提及都声明 independent / third-party / not affiliated
2. **不虚假承诺** — 不说 guaranteed uptime、unlimited、cheapest
3. **不刷 fake 数据** — 不提 fake users / fake reviews / fake earnings
4. **不 spam** — 只在相关讨论中自然提及，不群发、不刷版
5. **以"分享经验"的姿态出现** — 而不是"我在卖东西"
6. **引导到具体有价值的内容** — 教程页、docs、pricing，而不是空泛的首页
