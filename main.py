
import argparse
import os
from dotenv import load_dotenv
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.hn_fetcher import HackerNewsFetcher
from ml_subscriber.core.storage import JsonStorage
from ml_subscriber.core.visualization import ArticleVisualizer
from ml_subscriber.core.notification import TelegramNotifier

load_dotenv()  # 加载 .env 文件中的环境变量


def get_fetcher_for_source(source: str):
    if source == "hn":
        return HackerNewsFetcher()
    return ArxivFetcher()


def send_notifications(articles):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not found in environment variables.")
        return

    notifier = TelegramNotifier(bot_token, chat_id)
    if articles:
        print("Sending notification to Telegram...")
    else:
        print("No new articles. Sending reminder to Telegram...")
    notifier.send(articles)
    print("Notification sent.")


def main():
    """主函数，用于执行核心的爬取和存储逻辑。"""
    parser = argparse.ArgumentParser(description="Fetch and visualize ML/DL articles.")
    parser.add_argument('--fetch', action='store_true', help='Fetch articles from the configured source.')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization.')
    parser.add_argument('--output', type=str, default='output/articles.html', help='The output file name for visualization')
    parser.add_argument('--json-output', type=str, default='output/articles.json', help='The output file name for stored articles')
    parser.add_argument('--source', type=str, choices=['arxiv', 'hn'], default='arxiv', help='Content source to fetch from')
    args = parser.parse_args()

    json_output_path = args.json_output
    html_output_path = args.output

    if not (args.fetch or args.visualize):
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
            send_notifications([])
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
        if new_articles:
            send_notifications(new_articles)
        else:
            print("No new articles to notify; sending reminder.")
            send_notifications([])

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



if __name__ == "__main__":
    main()
