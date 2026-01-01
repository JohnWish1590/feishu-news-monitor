import feedparser
import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone
from deep_translator import GoogleTranslator

# ================= 配置区 =================
# 从环境变量读取 Webhook，确保隐私安全
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
KEYWORD = "监控"

# 监控列表
RSS_LIST = [
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.bloomberg.com/economics/news.rss",
    "https://cn.investing.com/rss/news_1.rss"
]

# 只看最近 16 分钟 (配合定时器)
TIME_WINDOW_MINUTES = 16 
# =========================================

def is_work_time():
    """判断是否在北京时间 08:00 - 22:00"""
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

def send_feishu_card(title_en, title_cn, link, date_str, source_name):
    if not FEISHU_WEBHOOK: return
    headers = {"Content-Type": "application/json"}
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange", 
            "title": {"tag": "plain_text", "content": f"【{source_name}】 {title_cn}"}
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**原文：** {title_en}\n**时间：** {date_str}"}},
            {"tag": "hr"},
            {"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "点击查看全文"}, "type": "primary", "url": link}]},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"来自：{KEYWORD} 机器人"}]}
        ]
    }
    try:
        requests.post(FEISHU_WEBHOOK, headers=headers, data=json.dumps({"msg_type": "interactive", "card": card_content}))
        print(f"✅ 推送成功: {title_cn[:10]}...")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def check_one_rss(url):
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0")
        if not feed.entries: return

        feed_title = feed.feed.get('title', 'Market')
        if "Bloomberg" in feed_title:
            if "Market" in feed_title: source_name = "彭博市场"
            elif "Economics" in feed_title: source_name = "彭博经济"
            else: source_name = "彭博社"
        elif "Investing" in feed_title: source_name = "英为财情"
        else: source_name = "财经资讯"

        for entry in feed.entries[:5]:
            title_origin = entry.title
            link = entry.link
            published_time = entry.published_parsed if hasattr(entry, 'published_parsed') else time.gmtime()
            pub_dt = datetime.fromtimestamp(time.mktime(published_time), timezone.utc)

            if pub_dt > (datetime.now(timezone.utc) - timedelta(minutes=TIME_WINDOW_MINUTES)):
                if is_work_time():
                    title_cn = translate_text(title_origin)
                    display_time = (pub_dt + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                    send_feishu_card(title_origin, title_cn, link, display_time, source_name)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    if not FEISHU_WEBHOOK:
        print("⚠️ 未检测到 Webhook，请检查 Secrets 设置")
    else:
        for rss_url in RSS_LIST:
            check_one_rss(rss_url)
