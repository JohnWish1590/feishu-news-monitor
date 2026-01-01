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

# 【测试模式】当前设为 1440 (24小时) 以便您看到效果
# ⚠️ 正式使用时请改回 16
TIME_WINDOW_MINUTES = 1440 

# 从 rss.txt 加载列表
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

def send_feishu_card(news_item):
    """
    发送单条消息，参数是字典对象
    """
    if not FEISHU_WEBHOOK: return
    
    # 解包数据
    title_en = news_item['title']
    title_cn = news_item['title_cn']
    link = news_item['link']
    date_str = news_item['display_time']
    source_name = news_item['source']

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

def fetch_news_from_url(url):
    """
    只抓取，不发送。返回抓取到的新闻列表。
    """
    collected_news = []
    print(f"🔍 正在检查: {url}")
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0")
        if not feed.entries: return []
        
        # 来源识别
        feed_title = feed.feed.get('title', 'Market')
        if "Bloomberg" in feed_title:
            if "Market" in feed_title: source_name = "彭博市场"
            elif "Economics" in feed_title: source_name = "彭博经济"
            elif "Tech" in feed_title: source_name = "彭博科技"
            else: source_name = "彭博社"
        elif "Investing" in feed_title: source_name = "英为财情"
        elif "Reuters" in feed_title: source_name = "路透社"
        elif "36Kr" in feed_title: source_name = "36氪"
        elif "Huxiu" in feed_title: source_name = "虎嗅"
        else: source_name = feed_title[:10].replace("RSS", "").strip()

        for entry in feed.entries[:5]:
            title_origin = entry.title
            link = entry.link
            published_time = entry.published_parsed if hasattr(entry, 'published_parsed') else time.gmtime()
            pub_dt = datetime.fromtimestamp(time.mktime(published_time), timezone.utc)
            
            # 时间过滤
            if pub_dt > (datetime.now(timezone.utc) - timedelta(minutes=TIME_WINDOW_MINUTES)):
                if is_work_time():
                    # 这里先不翻译，等排序后再翻译，或者现在翻译都可以
                    # 为了方便，先存起来
                    news_item = {
                        "title": title_origin,
                        "link": link,
                        "pub_dt": pub_dt, # 用于排序的原始时间对象
                        "display_time": (pub_dt + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
                        "source": source_name,
                        "title_cn": "" # 稍后填入
                    }
                    collected_news.append(news_item)
    except Exception as e: 
        print(f"Error checking {url}: {e}")
    
    return collected_news

if __name__ == "__main__":
    if not FEISHU_WEBHOOK:
        print("⚠️ 未检测到 Webhook")
    elif not RSS_LIST:
        print("⚠️ rss.txt 为空")
    else:
        print("📥 开始收集所有订阅源的新闻...")
        all_news_buffer = []
        
        # 1. 遍历所有 URL，收集新闻
        for rss_url in RSS_LIST:
            news_list = fetch_news_from_url(rss_url)
            all_news_buffer.extend(news_list)
            
        print(f"📊 共收集到 {len(all_news_buffer)} 条符合时间要求的新闻")

        # 2. 核心步骤：按时间排序
        # x['pub_dt'] 是时间对象。从小到大排序 = 从旧到新。
        # 这样飞书里最下面的是最新的。
        all_news_buffer.sort(key=lambda x: x['pub_dt'])

        # 3. 逐条翻译并推送
        for news in all_news_buffer:
            # 翻译标题 (放在这里是为了只翻译最终要发的，省资源)
            print(f"⚡ 正在处理: [{news['source']}] {news['title'][:10]}...")
            news['title_cn'] = translate_text(news['title'])
            
            # 发送
            send_feishu_card(news)
            # 稍微停顿一下，防止发太快顺序乱了
            time.sleep(1)
            
        print("🏁 所有任务完成")
