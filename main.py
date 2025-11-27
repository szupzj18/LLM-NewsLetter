
import argparse
import os
from dotenv import load_dotenv
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.hn_fetcher import HackerNewsFetcher
from ml_subscriber.core.storage import JsonStorage
from ml_subscriber.core.visualization import ArticleVisualizer
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier

load_dotenv()  # 加载 .env 文件中的环境变量


def get_fetcher_for_source(source: str):
    if source == "hn":
        return HackerNewsFetcher()
    return ArxivFetcher()


def send_notifications(articles, notifier_type, webhook_url=None):
    notifier = None
    if notifier_type == "telegram":
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            print("Telegram credentials not found in environment variables.")
            return
        notifier = TelegramNotifier(bot_token, chat_id)
    elif notifier_type == "webhook":
        if not webhook_url:
            print("Webhook URL not provided.")
            return
        notifier = WebhookNotifier(webhook_url)
    else:
        print(f"Unknown notifier type: {notifier_type}")
        return

    if articles:
        print(f"Sending notification via {notifier_type}...")
    else:
        print(f"No new articles. Sending reminder via {notifier_type}...")
    notifier.send(articles)
    print("Notification sent.")


def get_configured_notifiers(webhook_url):
    """检测已配置的通知渠道"""
    notifiers = []
    
    # 检查 Telegram 配置
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        notifiers.append("telegram")
    
    # 检查 Webhook 配置
    if webhook_url:
        notifiers.append("webhook")
    
    return notifiers


def main():
    """主函数，用于执行核心的爬取和存储逻辑。"""
    parser = argparse.ArgumentParser(description="Fetch and visualize ML/DL articles.")
    parser.add_argument('--fetch', action='store_true', help='Fetch articles from the configured source.')
    parser.add_argument('--notify', action='store_true', help='Send notifications for stored articles.')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization.')
    parser.add_argument('--output', type=str, default='output/articles.html', help='The output file name for visualization')
    parser.add_argument('--json-output', type=str, default='output/articles.json', help='The output file name for stored articles')
    parser.add_argument('--notifier', type=str, choices=['telegram', 'webhook', 'all'], help='The notification channel to use. Use "all" to notify all configured channels.')
    parser.add_argument('--webhook-url', type=str, help='The webhook URL to send notifications to.')
    parser.add_argument('--source', type=str, choices=['arxiv', 'hn'], default='arxiv', help='Content source to fetch from')
    args = parser.parse_args()

    json_output_path = args.json_output
    html_output_path = args.output

    webhook_url_env = os.environ.get("WEBHOOK_URL")
    webhook_url = args.webhook_url or webhook_url_env

    if not (args.fetch or args.visualize or args.notify):
        parser.print_help()
        return

    if args.fetch:
        # 1. 获取文章
        fetcher = get_fetcher_for_source(args.source)
        # 从选定的源获取文章；对 ArXiv 默认查询 cs.LG，对 HN 忽略查询参数
        default_query = "cat:cs.LG" if args.source == "arxiv" else ""
        articles = fetcher.fetch_articles(default_query, max_results=5)

        if not articles:
            print("未能获取到任何文章，仍会发送提示。")
            if args.notifier:
                send_notifications([], args.notifier, webhook_url)
            return

        print(f"成功获取到 {len(articles)} 篇文章，来源：{args.source}。")

        # 2. 存储文章
        storage = JsonStorage()

        # 如果输出目录不存在，创建它
        json_dir = os.path.dirname(json_output_path)
        if json_dir:
            os.makedirs(json_dir, exist_ok=True)

        # 比较新旧文章，只通知新文章
        try:
            existing_articles = storage.load_articles(json_output_path)
            existing_links = {article.link for article in existing_articles}
            new_articles = [article for article in articles if article.link not in existing_links]
        except FileNotFoundError:
            new_articles = articles

        storage.save_articles(articles, json_output_path)
        print(f"文章已保存至 {json_output_path}")
        print("如果需要可视化，请运行 '--visualize' 参数生成 HTML 文件。")

        # 3. 发送通知
        if args.notifier:
            # 确定要使用的通知渠道
            if args.notifier == "all":
                notifiers_to_use = get_configured_notifiers(webhook_url)
                if not notifiers_to_use:
                    print("No notification channels configured.")
            else:
                notifiers_to_use = [args.notifier]
            
            # 发送到所有指定的渠道
            articles_to_send = new_articles if new_articles else []
            if not new_articles:
                print("No new articles to notify; sending reminder.")
            
            for notifier_type in notifiers_to_use:
                send_notifications(articles_to_send, notifier_type, webhook_url)

    if args.visualize:
        storage = JsonStorage()
        articles = storage.load_articles(json_output_path)
        if not articles:
            print("未能加载到任何文章，请先运行 '--fetch' 参数获取文章。")
            return

        visualizer = ArticleVisualizer()

        # 确保 HTML 输出目录存在
        html_dir = os.path.dirname(html_output_path)
        if html_dir:
            os.makedirs(html_dir, exist_ok=True)

        visualizer.generate_html(articles, html_output_path)
        print(f"Visualization generated at {html_output_path}")

    if args.notify:
        if not args.notifier:
            print("请使用 --notifier 参数指定通知渠道 (telegram 或 webhook)")
            return

        storage = JsonStorage()
        try:
            articles = storage.load_articles(json_output_path)
        except FileNotFoundError:
            print(f"未找到文章文件 {json_output_path}，请先运行 '--fetch' 参数获取文章。")
            return

        send_notifications(articles, args.notifier, webhook_url)


if __name__ == "__main__":
    main()
