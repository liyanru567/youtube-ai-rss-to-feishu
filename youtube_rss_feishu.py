import feedparser
import requests
import os
import json
from datetime import datetime  # 可选：格式化发布时间

# 1. 从环境变量读取配置
YOUTUBE_RSS_URL = os.getenv("YOUTUBE_RSS_URL")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
SENT_VIDEOS_FILE = "sent_videos.txt"

# 2. 读取已推送的视频ID
def load_sent_videos():
    if os.path.exists(SENT_VIDEOS_FILE):
        with open(SENT_VIDEOS_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

# 3. 批量保存新推送的视频ID（核心修改：批量写入）
def save_sent_videos(video_ids):
    with open(SENT_VIDEOS_FILE, "a", encoding="utf-8") as f:
        # 每个ID一行，批量写入
        f.write("\n".join(video_ids) + "\n")

# 4. 发送组装后的单条飞书消息（核心修改）
def send_feishu_batch_message(new_videos):
    if not new_videos:  # 无新视频时直接返回
        print("无新视频，无需发送消息")
        return True
    
    # 格式化发布时间（可选：把ISO时间转成更易读的格式）
    def format_time(iso_time):
        try:
            return datetime.fromisoformat(iso_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except:
            return iso_time
    
    # 组装Markdown内容：每个视频一个条目
    video_items = []
    for idx, video in enumerate(new_videos, 1):
        video_items.append(f"""
{idx}. **{video['title']}**
> 发布时间：{format_time(video['publish_time'])}
> 视频链接：[点击查看]({video['video_url']})
""")
    
    # 飞书消息主体（单条消息包含所有新视频）
    msg_data = {
        "msg_type": "markdown",
        "content": {
            "title": f"🎬 YouTube新视频更新（共{len(new_videos)}个）",
            "text": "".join(video_items)  # 拼接所有视频条目
        }
    }
    
    try:
        response = requests.post(
            FEISHU_WEBHOOK,
            headers={"Content-Type": "application/json"},
            data=json.dumps(msg_data)
        )
        response.raise_for_status()
        print(f"批量消息发送成功：共{len(new_videos)}个视频")
        return True
    except Exception as e:
        print(f"批量消息发送失败：{e}")
        return False

# 5. 核心逻辑（批量处理）
def main():
    # 拉取RSS
    print(f"正在拉取YouTube RSS：{YOUTUBE_RSS_URL}")
    feed = feedparser.parse(YOUTUBE_RSS_URL)
    if feed.bozo != 0:
        print(f"RSS解析失败：{feed.bozo_exception}")
        return

    # 读取已推送ID
    sent_videos = load_sent_videos()
    print(f"已推送视频数量：{len(sent_videos)}")

    # 批量收集新视频（核心修改：先收集，再统一处理）
    new_videos = []
    new_video_ids = []  # 单独存ID，用于批量保存
    for entry in feed.entries:
        video_id = entry.get("yt_videoid")
        title = entry.get("title")
        video_url = entry.get("link")
        publish_time = entry.get("published")

        if video_id in sent_videos:
            print(f"视频已推送，跳过：{title}")
            continue
        
        # 收集新视频信息
        new_videos.append({
            "title": title,
            "video_url": video_url,
            "publish_time": publish_time
        })
        new_video_ids.append(video_id)

    # 发送单条批量消息 + 批量保存ID
    if send_feishu_batch_message(new_videos):
        if new_video_ids:  # 有新视频时才保存
            save_sent_videos(new_video_ids)
            print(f"批量保存{len(new_video_ids)}个视频ID")

if __name__ == "__main__":
    main()
