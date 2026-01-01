import feedparser
import requests
import json
import time
import os
import re
from datetime import datetime, timedelta, timezone
from deep_translator import GoogleTranslator

# ================= 配置区 =================
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
KEYWORD = "监控"
TIME_WINDOW_MINUTES = 16  # 正式运行时用 16
MAX_ARCHIVE_ITEMS = 800   # 保留最近800条

# =========================================
# 🎨 核心网页模板 (直接焊死在代码里，防止样式丢失)
# =========================================
HTML_TEMPLATE_HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Market Monitor | 市场情报</title>
    <style>
        :root { --bg: #f4f6f8; --text-main: #2c3e50; --text-sub: #7f8c8d; --card-bg: #ffffff; --line-color: #e0e0e0; --accent: #ff6600; --shadow: 0 4px 6px rgba(0,0,0,0.05); }
        @media (prefers-color-scheme: dark) { :root { --bg: #121212; --text-main: #e0e0e0; --text-sub: #a0a0a0; --card-bg: #1e1e1e; --line-color: #333; --shadow: 0 4px 6px rgba(0,0,0,0.3); } }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--bg); color: var(--text-main); margin: 0; padding: 0; line-height: 1.6; }
        
        /* 顶部标题栏 */
        .header { background: var(--card-bg); padding: 15px 20px; position: sticky; top: 0; z-index: 100; box-shadow: var(--shadow); border-bottom: 2px solid var(--accent); display: flex; align-items: center; justify-content: space-between; }
        .header h1 { margin: 0; font-size: 1.2rem; font-weight: 800; letter-spacing: 1px; }
        .header .status { font-size: 0.8rem; color: var(--accent); font-weight: bold; }
        
        .container { max-width: 800px; margin: 0 auto; padding: 30px 20px; }
        
        /* 时间线结构 */
        .timeline { position: relative; padding-left: 0; }
        .timeline::before { content: ''; position: absolute; left: 55px; top: 0; bottom: 0; width: 2px; background: var(--line-color); }
        
        /* 单条新闻块 */
        .timeline-item { position: relative; margin-bottom: 25px; display: flex; align-items: flex-start; }
        
        /* 左侧时间 (大字号) */
        .time-label { width: 45px; text-align: right; font-size: 0.95rem; font-weight: bold; color: var(--text-main); padding-top: 0px; margin-right: 25px; flex-shrink: 0; }
        /* 日期小字 */
        .date-label { font-size: 0.7rem; color: var(--text-sub); display: block; margin-top: 2px; }
        
        /* 圆点 */
        .dot { position: absolute; left: 51px; top: 6px; width: 10px; height: 10px; background: var(--bg); border: 2px solid var(--accent); border-radius: 50%; z-index: 1; }
        
        /* 右侧卡片 */
        .content-card { flex: 1; background: var(--card-bg); padding: 15px; border-radius: 8px; box-shadow: var(--shadow); transition: transform 0.2s ease; text-decoration: none; color: inherit; display: block; border-left: 3px solid transparent; }
        .content-card:hover { transform: translateY(-2px); border-left: 3px solid var(--accent); }
        
        .source-badge { display: inline-block; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: rgba(255, 102, 0, 0.1); color: var(--accent); font-weight: bold; margin-bottom: 8px; }
        
        .news-title { font-size: 1.1rem; font-weight: 700; margin: 0 0 6px 0; color: var(--text-main); }
        .news-origin { font-size: 0.85rem; color: var(--text-sub); font-style: italic; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Bloomberg | Market Flow</h1>
        <span class="status">● LIVE</span>
    </div>
    <div class="container">
        <div class="timeline">
            """

HTML_TEMPLATE_FOOTER = """
        </div>
        <div style="text-align: center; margin-top: 50px; color: var(--text-sub); font-size: 0.8rem;">
            —— End of Archive (Last 7 Days) ——
        </div>
    </div>
</body>
</html>
"""

def load_rss_list():
    rss_list = []
    if os.path.exists("rss.txt"):
        with open("rss.txt", "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    rss_list.append(line)
    return rss_list

RSS_LIST = load_rss_list()

def is_work_time():
    utc_now = datetime.now(timezone.utc)
    beijing_time = utc_now + timedelta(hours=8)
    if 8 <= beijing_time.hour < 22:
        return True
    return False

def translate_text(text):
    try:
        for char in text:
            if '\u4e00' <= char <= '\u9fff': return text
        translator = GoogleTranslator(source='auto', target='zh-CN')
        return translator.translate(text)
    except: return text

# --- 核心：自带修复功能的网页写入 ---
def update_html_archive(news_list):
    # 1. 生成新内容的 HTML (带时间线结构)
    new_html = ""
    for news in news_list:
        # 拆分时间：上面显示 10:30，下面小字显示日期
        time_hm = news['display_time'] # 10:30
        date_md = news['pub_dt'].strftime('%m-%d') # 01-02
        
        item = f"""
        <div class="timeline-item">
            <div class="time-label">
                {time_hm}
                <span class="date-label">{date_md}</span>
            </div>
            <div class="dot"></div>
            <a href="{news['link']}" target="_blank" class="content-card">
                <span class="source-badge">{news['source']}</span>
                <h3 class="news-title">{news['title_cn']}</h3>
                <div class="news-origin">{news['title']}</div>
            </a>
        </div>
        """
        new_html += item

    # 2. 读取旧内容 (尝试挽救之前的历史)
    old_items_content = ""
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
            # 利用正则提取所有已存在的 timeline-item
            matches = re.findall(r'(<div class="timeline-item">.*?</a>\s*</div>)', content, re.DOTALL)
            if matches:
                # 既然是倒序，旧内容应该放在后面
                old_items_content = "\n".join(matches)

    # 3. 拼接 新内容 + 旧内容
    # 注意：这里我们不直接 replace，而是完全重组整个文件
    # 这样能保证 Header 和 Style 永远是最新的
    full_content = new_html + "\n" + old_items_content

    # 4. 清理多余数据 (限制数量)
    # 再次用正则切分，确保数量不超标
    all_items = re.findall(r'(<div class="timeline-item">.*?</a>\s*</div>)', full_content, re.DOTALL)
    if len(all_items) > MAX_ARCHIVE_ITEMS:
        print(f"🧹 执行清理: 保留前 {MAX_ARCHIVE_ITEMS} 条")
        full_content = "\n".join(all_items[:MAX_ARCHIVE_ITEMS])
    
    # 5. 组合成最终网页
    final_html = HTML_TEMPLATE_HEADER.replace("", full_content) + HTML_TEMPLATE_FOOTER
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print("✅ 网页已全量重构更新 (样式修复完成)")

def send_grouped_card(source_name, news_list):
    if not FEISHU_WEBHOOK or not news_list: return
    headers = {"Content-Type": "application/json"}
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange", 
            "title": { "tag": "plain_text", "content": f"📊 {source_name} ({len(news_list)}条新消息)" }
        },
        "elements": []
    }
    for i, news in enumerate(news_list):
        element_div = {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🔹 **{news['title_cn']}**\n📄 原文：[{news['title']}]({news['link']})\n⏰ 时间：{news['display_time']}"
            }
        }
        card_content["elements"].append(element_div)
        if i < len(news_list) - 1: card_content["elements"].append({"tag": "hr"})

    card_content["elements"].append({"tag": "hr"})
    card_content["elements"].append({ "tag": "note", "elements": [{"tag": "plain_text", "content": f"来自：{KEYWORD} 机器人"}] })
    try:
        requests.post(FEISHU_WEBHOOK, headers=headers, data=json.dumps({"msg_type": "interactive", "card": card_content}))
    except: pass

def fetch_news_from_url(url):
    collected_news = []
    print(f"🔍 检查: {url}")
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0")
        if not feed.entries: return []
        feed_title = feed.feed.get('title', 'Market')
        if "Bloomberg" in feed_title:
            if "Market" in feed_title: source_name = "彭博市场"
            elif "Economics" in feed_title: source_name = "彭博经济"
            elif "Tech" in feed_title: source_name = "彭博科技"
            else: source_name = "彭博社"
        elif "Investing" in feed_title: source_name = "英为财情"
        elif "Reuters" in feed_title: source_name = "路透社"
        elif "36Kr" in feed_title: source_name = "36氪"
        elif "TechCrunch" in feed_title: source_name = "TechCrunch"
        else: source_name = feed_title[:10].replace("RSS", "").strip()

        for entry in feed.entries[:5]:
            title_origin = entry.title
            link = entry.link
            published_time = entry.published_parsed if hasattr(entry, 'published_parsed') else time.gmtime()
            pub_dt = datetime.fromtimestamp(time.mktime(published_time), timezone.utc)
            
            if pub_dt > (datetime.now(timezone.utc) - timedelta(minutes=TIME_WINDOW_MINUTES)):
                if is_work_time():
                    news_item = {
                        "title": title_origin,
                        "link": link,
                        "pub_dt": pub_dt,
                        "display_time": (pub_dt + timedelta(hours=8)).strftime('%H:%M'),
                        "source": source_name,
                        "title_cn": "" 
                    }
                    collected_news.append(news_item)
    except: pass
    return collected_news

if __name__ == "__main__":
    if not RSS_LIST:
        print("⚠️ 配置缺失")
    else:
        print("📥 开始抓取...")
        all_news_buffer = []
        for rss_url in RSS_LIST:
            news_list = fetch_news_from_url(rss_url)
            all_news_buffer.extend(news_list)

        all_news_buffer.sort(key=lambda x: x['pub_dt'])
        
        if all_news_buffer:
            print(f"⚡ 处理 {len(all_news_buffer)} 条新闻...")
            for news in all_news_buffer:
                news['title_cn'] = translate_text(news['title'])

            # 1. 重构网页 (倒序 + 修复样式)
            update_html_archive(reversed(all_news_buffer))

            # 2. 发送飞书
            news_by_source = {}
            for news in all_news_buffer:
                source = news['source']
                if source not in news_by_source: news_by_source[source] = []
                news_by_source[source].append(news)
            
            for source, news_list in news_by_source.items():
                send_grouped_card(source, news_list)
                time.sleep(1)
        else:
            print("📭 无新消息")
