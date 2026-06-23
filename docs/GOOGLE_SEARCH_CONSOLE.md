# Google Search Console 提交指南

## 目标

让 Google 知道你的网站存在，收录页面后别人搜索 "deepseek api gateway"、"openai compatible deepseek" 等关键词时可能找到你。

## 步骤 1：登录 Google Search Console

1. 打开 [https://search.google.com/search-console](https://search.google.com/search-console)
2. 用你的 Google 账号登录（没有就注册一个）
3. 点击左上角「添加资源」

## 步骤 2：添加网站

选择「网址前缀」类型，输入：

```
https://modelrelayapis.cc
```

点击「继续」。

## 步骤 3：验证域名所有权

Google 会要求你证明你是域名 owner。推荐用 **DNS 记录** 方式（最简单，不影响网站运行）：

1. Google 会给你一条 TXT 记录，类似：

   ```
   名称：modelrelayapis.cc
   值：google-site-verification=xxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

2. 去你的域名注册商（NameSilo）DNS 管理页面
3. 添加一条 TXT 记录，把 Google 给的值填进去
4. 等 1-5 分钟后回 Google Search Console 点击「验证」

如果不想用 DNS，也可以选「HTML 文件上传」——我可以帮你在 static 目录放一个验证文件。

## 步骤 4：提交 sitemap

验证通过后：

1. 左侧菜单点击「Sitemap」
2. 在「添加新的 Sitemap」输入框中填写：

   ```
   sitemap.xml
   ```

3. 点击「提交」
4. 状态显示「成功」即可

## 步骤 5：等待

- sitemap 提交后 Google 不会马上收录所有页面
- 通常 1-3 天内开始出现，完全收录可能需要几周
- 可以在「涵盖范围」里看到哪些页面已收录、哪些有问题
- **这不代表马上有排名**，只是让 Google 知道页面存在
- 排名取决于内容质量、外链、用户搜索行为等，是长期过程

## 后续

- 每次新增页面后，更新 sitemap.xml 并重新提交
- 定期检查「涵盖范围」看有没有 404 或错误
- 不要频繁重复提交同一个 sitemap，Google 会自己定期抓取

---

> 你不需要邀请码，不需要付费，Google Search Console 完全免费。
