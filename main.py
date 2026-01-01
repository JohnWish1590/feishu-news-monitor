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

# 加载订阅源
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

def send_grouped_card(source_name, news_list):
    """
    发送聚合卡片：一张卡片包含多条新闻
    """
    if not FEISHU_WEBHOOK: return
    if not news_list: return

    headers = {"Content-Type": "application/json"}
    
    # 1. 构建卡片头部 (Header)
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange", 
            "title": {
                "tag": "plain_text", 
                "content": f"📊 {source_name} ({len(news_list)}条新消息)"
            }
        },
        "elements": []
    }

    # 2. 动态构建中间的新闻列表 (Elements)
    # 循环把每一条新闻加进去
    for i, news in enumerate(news_list):
        # 每一条新闻是一个 div
        element_div = {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🔹 **{news['title_cn']}**\n📄 原文：[{news['title']}]({news['link']})\n⏰ 时间：{news['display_time']}"
            }
        }
        card_content["elements"].append(element_div)
        
        # 如果不是最后一条，加一个分割线，好看一点
        if i < len(news_list) - 1:
            card_content["elements"].append({"tag": "hr"})

    # 3. 底部署名
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
                        "display_time": (pub_dt + timedelta(hours=8)).strftime('%H:%M'), # 聚合模式下，时间只显示 时:分 就够了
                        "source": source_name,
                        "title_cn": "" 
                    }
                    collected_news.append(news_item)
    except Exception as e: 
        print(f"Error: {e}")
    
    return collected_news

if __name__ == "__main__":
    if not FEISHU_WEBHOOK or not RSS_LIST:
        print("⚠️ 配置缺失")
    else:
        print("📥 开始抓取...")
        all_news_buffer = []
        
        # 1. 抓取所有新闻
        for rss_url in RSS_LIST:
            news_list = fetch_news_from_url(rss_url)
            all_news_buffer.extend(news_list)

        # 2. 分组逻辑 (Grouping)
        # 创建一个字典： { "彭博市场": [新闻1, 新闻2], "36氪": [新闻A] }
        news_by_source = {}
        
        # 先按时间排个序，保证卡片里的新闻是从旧到新的
        all_news_buffer.sort(key=lambda x: x['pub_dt'])

        for news in all_news_buffer:
            source = news['source']
            if source not in news_by_source:
                news_by_source[source] = []
            news_by_source[source].append(news)

        # 3. 按来源发送聚合卡片
        if not news_by_source:
            print("📭 暂无新消息")
        else:
            for source, news_list in news_by_source.items():
                print(f"📦 正在打包 {source} 的 {len(news_list)} 条新闻...")
                
                # 统一翻译 (放在发送前翻译)
                for news in news_list:
                    news['title_cn'] = translate_text(news['title'])
                
                # 发送这一组
                send_grouped_card(source, news_list)
                time.sleep(1) # 防止发太快
