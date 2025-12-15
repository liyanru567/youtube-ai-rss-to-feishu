import feedparser
import requests
import os
import json

# 1. 从环境变量读取配置（避免硬编码敏感信息）
YOUTUBE_RSS_URL = os.getenv("YOUTUBE_RSS_URL")  # YouTube RSS地址
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")    # 飞书机器人Webhook
SENT_VIDEOS_FILE = "sent_videos.txt"            # 记录已推送视频ID的文件

# 2. 读取已推送的视频ID（避免重复发送）
def load_sent_videos():
    if os.path.exists(SENT_VIDEOS_FILE):
        with open(SENT_VIDEOS_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())  # 用集合存储，方便去重
    return set()

# 3. 保存新推送的视频ID
def save_sent_video(video_id):
    with open(SENT_VIDEOS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")

# 4. 调用飞书Webhook发送消息
def send_feishu_message(title, video_url, publish_time):
    # 飞书消息格式（支持Markdown，可自定义）
    msg_data = {
        "msg_type": "markdown",
        "content": {
            "title": "🎬 YouTube新视频更新",
            "text": f"""
### {title}
> 发布时间：{publish_time}
> 视频链接：[点击查看]({video_url})
"""
        }
    }
    try:
        response = requests.post(
            FEISHU_WEBHOOK,
            headers={"Content-Type": "application/json"},
            data=json.dumps(msg_data)
        )
        response.raise_for_status()  # 抛出HTTP错误
        print(f"飞书消息发送成功：{title}")
        return True
    except Exception as e:
        print(f"飞书消息发送失败：{e}")
        return False

# 5. 核心逻辑：拉取RSS→解析→推送新视频
def main():
    # 拉取YouTube RSS
    print(f"正在拉取YouTube RSS：{YOUTUBE_RSS_URL}")
    feed = feedparser.parse(YOUTUBE_RSS_URL)
    if feed.bozo != 0:
        print(f"RSS解析失败：{feed.bozo_exception}")
        return

    # 读取已推送的视频ID
    sent_videos = load_sent_videos()
    print(f"已推送视频数量：{len(sent_videos)}")

    # 遍历RSS中的视频（按发布时间倒序）
    for entry in feed.entries:
        video_id = entry.get("yt_videoid")  # 提取视频ID
        title = entry.get("title")          # 视频标题
        video_url = entry.get("link")       # 视频链接
        publish_time = entry.get("published")  # 发布时间（ISO格式）

        # 跳过已推送的视频
        if video_id in sent_videos:
            print(f"视频已推送，跳过：{title}")
            continue

        # 发送飞书消息
        if send_feishu_message(title, video_url, publish_time):
            save_sent_video(video_id)  # 发送成功后记录ID

if __name__ == "__main__":
    main()
