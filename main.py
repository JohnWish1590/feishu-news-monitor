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
TIME_WINDOW_MINUTES = 16 

# 【核心升级】从 rss.txt 文件加载监控列表
def load_rss_list():
    rss_list = []
    # 检查文件是否存在
    if os.path.exists("rss.txt"):
        with open("rss.txt", "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 忽略空行和以#开头的注释行
                if line and not line.startswith("#"):
                    rss_list.append(line)
    return rss_list

# 加载列表
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
    print(f"🔍 正在检查: {url}")
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0")
        if not feed.entries: return
        
        # 智能识别来源名称
        feed_title = feed.feed.get('title', 'Market')
        if "Bloomberg" in feed_title:
            if "Market" in feed_title: source_name = "彭博市场"
            elif "Economics" in feed_title: source_name = "彭博经济"
            elif "Tech" in feed_title: source_name = "彭博科技"
            else: source_name = "彭博社"
        elif "Investing" in feed_title: source_name = "英为财情"
        elif "Reuters" in feed_title: source_name = "路透社" # 顺手加个路透
        else: 
            # 如果是未知的源，截取标题前10个字
            source_name = feed_title[:10].replace("RSS", "").strip()

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
    except Exception as e: print(f"Error checking {url}: {e}")

if __name__ == "__main__":
    if not FEISHU_WEBHOOK:
        print("⚠️ 未检测到 Webhook，请检查 Secrets 设置")
    elif not RSS_LIST:
        print("⚠️ rss.txt 为空或不存在，请添加订阅源")
    else:
        print(f"📂 已加载 {len(RSS_LIST)} 个订阅源")
        for rss_url in RSS_LIST:
            check_one_rss(rss_url)
