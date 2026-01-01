import feedparser
import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone
from deep_translator import GoogleTranslator

# ================= 配置区 =================
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
KEYWORD = "监控"

# ⚠️ 测试完记得把这个改回 16
TIME_WINDOW_MINUTES = 1440 

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

# --- 新增功能：把新闻写入 index.html (支持倒序) ---
def update_html_archive(news_list):
    """读取 index.html，把新新闻插入到标记位"""
    if not os.path.exists("index.html"): return
    
    # 1. 生成新内容的 HTML 片段
    new_html = ""
    for news in news_list:
        # HTML 卡片样式
        card = f"""
        <a href="{news['link']}" target="_blank">
            <div class="news-card">
                <div class="news-header">
                    <span class="source-tag">{news['source']}</span>
                    <span class="time-tag">{news['display_time']}</span>
                </div>
                <div class="news-title">{news['title_cn']}</div>
                <div class="news-meta">原文：{news['title']}</div>
            </div>
        </a>
        """
        new_html += card

    # 2. 读取原文件并插入
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 关键点：找到标记位，把新内容插在标记后面
    # 因为我们传入的 list 已经是【新->旧】排序的，所以插在最上面正好
    marker = ""
    if marker in content:
        new_content = content.replace(marker, marker + "\n" + new_html)
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✅ 网页存档已更新 (最新新闻在顶部)")

def send_grouped_card(source_name, news_list):
    """发送聚合卡片"""
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
        print(f"✅ [聚合推送] {source_name} - {len(news_list)} 条内容已发送")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def fetch_news_from_url(url):
    collected_news = []
    print(f"🔍 检查: {url}")
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0")
        if not feed.entries: return []
        
        feed_title = feed.feed.get('title', 'Market')
        # 来源判断逻辑
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
                        "title_cn": "" # 稍后统一填
                    }
                    collected_news.append(news_item)
    except Exception as e: 
        print(f"Error: {e}")
    
    return collected_news

if __name__ == "__main__":
    if not RSS_LIST:
        print("⚠️ 配置缺失: 请检查 rss.txt")
    else:
        print("📥 开始抓取...")
        all_news_buffer = []
        for rss_url in RSS_LIST:
            news_list = fetch_news_from_url(rss_url)
            all_news_buffer.extend(news_list)

        # 排序：先按【旧 -> 新】排好
        # 为什么要旧到新？因为飞书卡片里读起来习惯是从上往下读
        all_news_buffer.sort(key=lambda x: x['pub_dt'])
        
        if all_news_buffer:
            print(f"⚡ 正在处理 {len(all_news_buffer)} 条新闻 (翻译中)...")
            # 统一翻译
            for news in all_news_buffer:
                news['title_cn'] = translate_text(news['title'])

            # === 动作 1: 更新网页存档 (倒序) ===
            # 这里用了 reversed()，把列表变成【新 -> 旧】，从而实现最新新闻在网页最顶部
            update_html_archive(reversed(all_news_buffer))

            # === 动作 2: 发送飞书聚合卡片 ===
            # 这里的 all_news_buffer 依然是【旧 -> 新】，符合阅读习惯
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
