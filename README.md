(该项目已经关停）

# 📈 Global Market Monitor (个人专属财经情报站)

> 打造属于你的“彭博终端”：飞书即时推送 + 沉浸式网页时光机。
> **零成本 · 零代码 · 省流稳定版**

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.9-green)
![Status](https://img.shields.io/badge/status-active-orange)

## ✨ 核心功能

这是一个基于 GitHub Actions 的自动化机器人，它能帮你盯着全球的财经和科技新闻，并自动整理汇报。

| 📱 飞书推送 (即时) | 🌏 网页时光机 (归档) |
| :--- | :--- |
| **聚合卡片**：避免消息刷屏，多条新闻打包推送。<br>**自动翻译**：英文新闻自动翻译为中文标题。<br>**一键直达**：点击直接跳转原文。 | **彭博风格**：极简时间轴设计，专业易读。<br>**自动同步**：手机/电脑浏览器随时访问，无需翻墙。<br>**自动清理**：只保留最近一周新闻，加载飞快。 |

---

## 🕒 运行机制 (已优化)

为了节省 GitHub Actions 免费额度，同时保证工作时间的即时性，本项目采用了**“省流模式”**配置：

* **工作时间**：每天 **08:00 - 20:00** (北京时间)。
* **更新频率**：每 **30分钟** 自动巡查一次。
* **休眠模式**：夜间 (20:00 - 次日08:00) 自动停止运行，不消耗额度，也不打扰休息。

---

## 🚀 5分钟部署教程 (傻瓜式)

不需要懂编程，只要有一个 GitHub 账号，跟着做即可。

### 第一步：获取飞书 Webhook 🤖
1. 在飞书电脑端，拉一个群（或者只拉你自己）。
2. 点击群设置 -> **群机器人** -> **添加机器人** -> **自定义机器人**。
3. **【关键设置】** 在“安全设置”中勾选 **“自定义关键词”**，并填入：`监控` (必须是这两个字，否则不发消息)。
4. 点击“添加”，**复制生成的 Webhook 地址** (以 `https://open.feishu.cn/...` 开头)。

### 第二步：一键复刻项目 📋
1. 点击本项目页面右上角的绿色按钮 **"Use this template"** -> **"Create a new repository"**。
2. 给你的仓库起个名字（例如 `my-news-station`），选择 **Public** (为了能展示网页)，点击 **Create repository**。

### 第三步：配置密钥 🔑
1. 进入你新创建的仓库，点击上方的 **Settings** (设置)。
2. 在左侧栏找到 **Secrets and variables** -> 点击 **Actions**。
3. 点击 **New repository secret** (绿色按钮)。
4. **Name** 填：`FEISHU_WEBHOOK` (必须全大写)。
5. **Secret** 填：第一步里复制的飞书地址。
6. 点击 **Add secret**。

### 第四步：开启网页服务 (重要！) 🌐
1. 依然在 **Settings** 页面，点击左侧边栏下方的 **Pages**。
2. 在 **Build and deployment** 区域：
   - **Source** 选择 `Deploy from a branch`。
   - **Branch** 选择 `main` (或者 master)，文件夹选择 `/(root)`。
3. 点击 **Save**。

### 第五步：启动机器人 ⚡
1. 点击仓库上方的 **Actions** 标签。
2. 你会看到一个警告，点击绿色按钮 **"I understand my workflows..."**。
3. 在左侧点击 **News Monitor** -> 右侧点击 **Run workflow** -> **Run workflow**。
4. **见证奇迹的时刻：**
   - 你的飞书会收到一条测试消息。
   - 等待约 1 分钟后，在 **Settings -> Pages** 页面顶部，你会看到你的专属网址（例如 `https://你的名字.github.io/my-news-station/`），点开就是你的财经时间轴！

---

## 🔧 如何修改监控源 (RSS)

想看科技新闻？想看路透社？改这里：

1. 在仓库文件列表中，点击 **`rss.txt`** 文件。
2. 点击右上角的小铅笔图标 ✏️ (Edit)。
3. **一行一个链接**，粘贴你想要的 RSS 地址。
   *(不想看的源可以在前面加 `#` 号注释掉)*
4. 点击 **Commit changes** 保存。
5. 下次运行时，机器人就会自动加载新列表了！

#### 📝 推荐的高质量源：
```text
# === 财经类 ===
[https://feeds.bloomberg.com/markets/news.rss](https://feeds.bloomberg.com/markets/news.rss)      # 彭博市场
[https://feeds.bloomberg.com/economics/news.rss](https://feeds.bloomberg.com/economics/news.rss)    # 彭博经济
[https://cn.investing.com/rss/news_1.rss](https://cn.investing.com/rss/news_1.rss)           # 英为财情

# === 科技类 ===
[https://techcrunch.com/feed/](https://techcrunch.com/feed/)                      # TechCrunch (全球科技风向)
[https://36kr.com/feed](https://36kr.com/feed)                             # 36氪 (创投)
[https://www.theverge.com/rss/index.xml](https://www.theverge.com/rss/index.xml)            # The Verge (数码/文化)
