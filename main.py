
import argparse
import os
from dotenv import load_dotenv
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.hn_fetcher import HackerNewsFetcher
from ml_subscriber.core.storage import JsonStorage
from ml_subscriber.core.visualization import ArticleVisualizer
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier

load_dotenv()


# ============================================================================
# 工具函数
# ============================================================================

def get_fetcher_for_source(source: str):
    """根据来源返回对应的 fetcher"""
    if source == "hn":
        return HackerNewsFetcher()
    return ArxivFetcher()


def get_webhook_url(args):
    """获取 webhook URL，优先使用命令行参数"""
    return args.webhook_url or os.environ.get("WEBHOOK_URL")


def get_configured_notifiers(webhook_url):
    """检测已配置的通知渠道"""
    notifiers = []
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        notifiers.append("telegram")
    
    if webhook_url:
        notifiers.append("webhook")
    
    return notifiers


def resolve_notifiers(notifier_arg, webhook_url):
    """解析要使用的通知渠道列表"""
    if not notifier_arg:
        return []
    if notifier_arg == "all":
        return get_configured_notifiers(webhook_url)
    return [notifier_arg]


def ensure_dir(file_path):
    """确保文件所在目录存在"""
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def create_notifier(notifier_type, webhook_url):
    """创建通知器实例"""
    if notifier_type == "telegram":
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            print("Telegram credentials not found in environment variables.")
            return None
        return TelegramNotifier(bot_token, chat_id)
    
    if notifier_type == "webhook":
        if not webhook_url:
            print("Webhook URL not provided.")
            return None
        return WebhookNotifier(webhook_url)
    
    print(f"Unknown notifier type: {notifier_type}")
    return None


def send_notification(articles, notifier_type, webhook_url):
    """发送单个通知"""
    notifier = create_notifier(notifier_type, webhook_url)
    if not notifier:
        return
    
    status = "Sending notification" if articles else "No new articles. Sending reminder"
    print(f"{status} via {notifier_type}...")
    notifier.send(articles)
    print("Notification sent.")


def broadcast_notifications(articles, notifier_types, webhook_url):
    """向多个渠道发送通知"""
    if not notifier_types:
        print("No notification channels configured.")
        return
    
    for notifier_type in notifier_types:
        send_notification(articles, notifier_type, webhook_url)


# ============================================================================
# 命令处理函数
# ============================================================================

def handle_fetch(args, webhook_url):
    """处理 --fetch 命令：抓取文章并可选发送通知"""
    # 获取文章
    fetcher = get_fetcher_for_source(args.source)
    query = "cat:cs.LG" if args.source == "arxiv" else ""
    articles = fetcher.fetch_articles(query, max_results=5)

    if not articles:
        print("未能获取到任何文章，仍会发送提示。")
        notifiers = resolve_notifiers(args.notifier, webhook_url)
        broadcast_notifications([], notifiers, webhook_url)
        return

    print(f"成功获取到 {len(articles)} 篇文章，来源：{args.source}。")

    # 存储文章
    storage = JsonStorage()
    ensure_dir(args.json_output)
    
    # 计算新文章（增量）
    existing = storage.load_articles(args.json_output)
    existing_links = {a.link for a in existing}
    new_articles = [a for a in articles if a.link not in existing_links]

    storage.save_articles(articles, args.json_output)
    print(f"文章已保存至 {args.json_output}")

    # 发送通知
    notifiers = resolve_notifiers(args.notifier, webhook_url)
    if not notifiers:
        return
    
    if not new_articles:
        print("No new articles to notify; sending reminder.")
    broadcast_notifications(new_articles, notifiers, webhook_url)


def handle_visualize(args):
    """处理 --visualize 命令：生成可视化 HTML"""
    storage = JsonStorage()
    articles = storage.load_articles(args.json_output)
    
    if not articles:
        print("未能加载到任何文章，请先运行 '--fetch' 参数获取文章。")
        return

    ensure_dir(args.output)
    visualizer = ArticleVisualizer()
    visualizer.generate_html(articles, args.output)
    print(f"Visualization generated at {args.output}")


def handle_notify(args, webhook_url):
    """处理 --notify 命令：发送已存储文章的通知"""
    if not args.notifier:
        print("请使用 --notifier 参数指定通知渠道 (telegram, webhook 或 all)")
        return

    storage = JsonStorage()
    articles = storage.load_articles(args.json_output)
    
    if not articles:
        print(f"未找到文章文件 {args.json_output}，请先运行 '--fetch' 参数获取文章。")
        return

    notifiers = resolve_notifiers(args.notifier, webhook_url)
    broadcast_notifications(articles, notifiers, webhook_url)


# ============================================================================
# 主函数
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Fetch and visualize ML/DL articles.")
    parser.add_argument('--fetch', action='store_true', 
                        help='Fetch articles from the configured source.')
    parser.add_argument('--notify', action='store_true', 
                        help='Send notifications for stored articles.')
    parser.add_argument('--visualize', action='store_true', 
                        help='Generate visualization.')
    parser.add_argument('--output', type=str, default='output/articles.html', 
                        help='The output file name for visualization')
    parser.add_argument('--json-output', type=str, default='output/articles.json', 
                        help='The output file name for stored articles')
    parser.add_argument('--notifier', type=str, choices=['telegram', 'webhook', 'all'], 
                        help='The notification channel to use. Use "all" to notify all configured channels.')
    parser.add_argument('--webhook-url', type=str, 
                        help='The webhook URL to send notifications to.')
    parser.add_argument('--source', type=str, choices=['arxiv', 'hn'], default='arxiv', 
                        help='Content source to fetch from')
    return parser


def main():
    """主函数入口"""
    parser = parse_args()
    args = parser.parse_args()

    if not (args.fetch or args.visualize or args.notify):
        parser.print_help()
        return

    webhook_url = get_webhook_url(args)

    if args.fetch:
        handle_fetch(args, webhook_url)

    if args.visualize:
        handle_visualize(args)

    if args.notify:
        handle_notify(args, webhook_url)


if __name__ == "__main__":
    main()
