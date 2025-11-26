
import argparse
import os
from dotenv import load_dotenv
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.storage import JsonStorage
from ml_subscriber.core.visualization import ArticleVisualizer
from ml_subscriber.core.notification import TelegramNotifier

load_dotenv()  # 加载 .env 文件中的环境变量

def main():
    """主函数，用于执行核心的爬取和存储逻辑。"""
    parser = argparse.ArgumentParser(description="Fetch and visualize ArXiv articles.")
    parser.add_argument('--fetch', action='store_true', help='Fetch ArXiv articles.')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization.')
    parser.add_argument('--output', type=str, default='articles.html', help='The output file name for visualization')
    args = parser.parse_args()

    if not (args.fetch or args.visualize):
        parser.print_help()
        return

    if args.fetch:
        # 1. 获取文章
        fetcher = ArxivFetcher()
        # 从 ArXiv 查询最新的 5 篇 cs.LG (Learning) 类别的文章
        articles = fetcher.fetch_articles("cat:cs.LG", max_results=5)

        if not articles:
            print("未能获取到任何文章，程序退出。")
            return

        print(f"成功获取到 {len(articles)} 篇文章。")

        # 2. 存储文章
        storage = JsonStorage()
        output_filename = "articles.json"

        # 比较新旧文章，只通知新文章
        try:
            existing_articles = storage.load_articles(output_filename)
            existing_links = {article.link for article in existing_articles}
            new_articles = [article for article in articles if article.link not in existing_links]
        except FileNotFoundError:
            new_articles = articles

        storage.save_articles(articles, output_filename)
        print(f"文章已保存至 {output_filename}")

        # 3. 发送通知
        if new_articles:
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")

            if bot_token and chat_id:
                print("Sending notification to Telegram...")
                notifier = TelegramNotifier(bot_token, chat_id)
                notifier.send(new_articles)
                print("Notification sent.")
            else:
                print("Telegram credentials not found in environment variables.")
        else:
            print("No new articles to notify.")

    if args.visualize:
        storage = JsonStorage()
        articles = storage.load_articles("articles.json")
        if not articles:
            print("未能加载到任何文章，请先运行 '--fetch' 参数获取文章。")
            return

        visualizer = ArticleVisualizer()
        visualizer.generate_html(articles, args.output)
        print(f"Visualization generated at {args.output}")



if __name__ == "__main__":
    main()
