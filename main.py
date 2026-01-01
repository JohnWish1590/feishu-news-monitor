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

# 1. 正常运行模式 (只看过去16分钟)
TIME_WINDOW_MINUTES = 16

# 2. 【核心修改】保留一周左右的数据量
# 每天约60次运行 * 7天 * 每次平均2条 = 840条
# 设定为 800，文件大小仅约 300KB，非常安全
MAX_ARCHIVE_ITEMS = 800 

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
# =========================================

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

# --- 网页写入函数 (带自动清理) ---
def update_html_archive(news_list):
    if not os.path.exists("index.html"): return
    
    # 1. 生成新内容的 HTML
    new_html = ""
    for news in news_list:
        item = f"""
        <div class="timeline-item">
            <div class="time-label">{news['display_time']}</div>
            <div class="dot"></div>
            <a href="{news['link']}" target="_blank" class="content-card">
                <span class="source-badge">{news['source']}</span>
                <h3 class="news-title">{news['title_cn']}</h3>
                <div class="news-origin">{news['title']}</div>
            </a>
        </div>
        """
        new_html += item

    # 2. 读取文件
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 3. 插入新内容
    marker = ""
    if marker in content:
        content = content.replace(marker, marker + "\n" + new_html)
        
        # === 4. 清理旧新闻 (控制在一周左右) ===
        # 查找所有的 timeline-item
        item_matches = [m.start() for m in re.finditer(r'<div class="timeline-item">', content)]
        
        # 如果超过限制 (800条)
        if len(item_matches) > MAX_ARCHIVE_ITEMS:
            print(f"🧹 触发清理: 当前 {len(item_matches)} 条，保留最新的 {MAX_ARCHIVE_ITEMS} 条")
            
            # 找到第 801 条的开始位置，把后面的切掉
            cut_off_index = item_matches[MAX_ARCHIVE_ITEMS]
            kept_content = content[:cut_off_index]
            
            # 补全页脚
            footer = """
        </div>
        <div style="text-align: center; margin-top: 50px; color: var(--text-sub); font-size: 0.8rem;">
            —— End of Archive (Last 7 Days) ——
        </div>
    </div>
</body>
</html>"""
            content = kept_content + footer
            
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ 网页已更新")

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
        if i < len(news_list) - 1:
            card_content["elements"].append({"tag": "hr"})

    card_content["elements"].append({"tag": "hr"})
    card_content["elements"].append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"来自：{KEYWORD} 机器人 | 自动聚合模式"}]
    })

    try:
        requests.post(FEISHU_WEBHOOK, headers=headers, data=json.dumps({"msg_type": "interactive", "card": card_content}))
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def fetch_news_from_url(url):
    collected_news = []
    print(f"🔍 检查: {url}")
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0")
        if not feed.entries: return []
        
        feed_title = feed.feed.get('title', 'Market')
        # 简单来源判断
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
    except Exception as e: 
        print(f"Error: {e}")
    
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
            print(f"⚡ 正在处理 {len(all_news_buffer)} 条新闻...")
            for news in all_news_buffer:
                news['title_cn'] = translate_text(news['title'])

            # 动作1: 倒序写网页 (限制800条)
            update_html_archive(reversed(all_news_buffer))

            # 动作2: 发送飞书
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
