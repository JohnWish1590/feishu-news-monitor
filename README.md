# 📈 Feishu Financial News Monitor (飞书财经新闻机器人)

> 一个基于 GitHub Actions 的 Serverless 财经新闻监控机器人。零成本、即时推送、自动翻译、彭博终端风格。

## ✨ 项目亮点

你是否想要第一时间获取 **Bloomberg** 或 **Investing.com** 的突发新闻？
这个 GitHub 模板可以让你在 3 分钟内拥有一个属于自己的财经情报机器人。

| 效果图 | 特性 |
| :---: | :--- |
| <img src="https://github.com/user-attachments/assets/774956e1-5ac1-4dbe-9898-7e5977369427" width="300" /> | ✅ **零成本**：白嫖 GitHub Actions 免费运行。<br><br>✅ **彭博风格**：还原经典金融终端“橙色警报”风格。<br><br>✅ **隐私安全**：Webhook 只有你自己知道。<br><br>✅ **自动双语**：英文快讯自动翻译为中文。 |

---

## 🚀 3分钟部署教程

### 第一步：获取飞书 Webhook 🤖
1. 在飞书群聊中 -> 设置 -> 群机器人 -> 添加机器人 -> **自定义机器人**。
2. 安全设置勾选 **“自定义关键词”**，填入：`监控`。
3. 复制生成的 webhook 地址。

### 第二步：复刻项目 📋
1. 点击本项目页面右上角的绿色按钮 **"Use this template"** -> **"Create a new repository"**。
2. 起个名字，点击 Create。

### 第三步：配置密钥 (最关键！) 🔑
1. 进入你新创建的仓库，点击 **Settings**。
2. 左侧找 **Secrets and variables** -> **Actions**。
3. 点击 **New repository secret**。
4. **Name** 填：`FEISHU_WEBHOOK`。
5. **Secret** 填：你的飞书 Webhook 地址。
6. 点击 Add secret 保存。

### 第四步：启动 ⚡
1. 点击仓库上方的 **Actions** 标签。
2. 点击 **News Monitor** -> **Run workflow**。
3. 完成！以后它每15分钟自动运行。
