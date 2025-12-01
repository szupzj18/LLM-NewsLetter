
import argparse
import os
from dotenv import load_dotenv
from ml_subscriber.core.arxiv_fetcher import ArxivFetcher
from ml_subscriber.core.hn_fetcher import HackerNewsFetcher
from ml_subscriber.core.storage import JsonStorage
from ml_subscriber.core.visualization import ArticleVisualizer
from ml_subscriber.core.notification import TelegramNotifier, WebhookNotifier
from ml_subscriber.core.translator import create_translator

load_dotenv()


# ============================================================================
# Utility Functions
# ============================================================================

def get_fetcher_for_source(source: str):
    """Return the appropriate fetcher for the given source."""
    if source == "hn":
        return HackerNewsFetcher()
    return ArxivFetcher()


def get_webhook_url(args):
    """Get webhook URL, preferring command line argument over environment variable."""
    return args.webhook_url or os.environ.get("WEBHOOK_URL")


def get_configured_notifiers(webhook_url):
    """Detect configured notification channels."""
    notifiers = []
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        notifiers.append("telegram")
    
    if webhook_url:
        notifiers.append("webhook")
    
    return notifiers


def resolve_notifiers(notifier_arg, webhook_url):
    """Resolve the list of notification channels to use."""
    if not notifier_arg:
        return []
    if notifier_arg == "all":
        return get_configured_notifiers(webhook_url)
    return [notifier_arg]


def ensure_dir(file_path):
    """Ensure the directory for a file path exists."""
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def get_translator():
    """Create a translator instance based on environment configuration."""
    deepl_api_key = os.environ.get("DEEPL_API_KEY")
    use_free = os.environ.get("USE_FREE_TRANSLATOR", "true").lower() == "true"
    
    if deepl_api_key:
        print("DeepL translation enabled.")
        return create_translator(deepl_api_key=deepl_api_key)
    elif use_free:
        print("Free Google translation enabled.")
        return create_translator(use_free=True)
    return create_translator(use_free=False)


def create_notifier(notifier_type, webhook_url, translator=None):
    """Create a notifier instance for the given type."""
    if notifier_type == "telegram":
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            print("Telegram credentials not found in environment variables.")
            return None
        return TelegramNotifier(bot_token, chat_id, translator=translator)
    
    if notifier_type == "webhook":
        if not webhook_url:
            print("Webhook URL not provided.")
            return None
        return WebhookNotifier(webhook_url, translator=translator)
    
    print(f"Unknown notifier type: {notifier_type}")
    return None


def send_notification(articles, notifier_type, webhook_url, translator=None):
    """Send a single notification."""
    notifier = create_notifier(notifier_type, webhook_url, translator=translator)
    if not notifier:
        return
    
    status = "Sending notification" if articles else "No new articles. Sending reminder"
    print(f"{status} via {notifier_type}...")
    notifier.send(articles)
    print("Notification sent.")


def broadcast_notifications(articles, notifier_types, webhook_url, translator=None):
    """Broadcast notifications to multiple channels."""
    if not notifier_types:
        print("No notification channels configured.")
        return
    
    for notifier_type in notifier_types:
        send_notification(articles, notifier_type, webhook_url, translator=translator)


# ============================================================================
# Command Handlers
# ============================================================================

def handle_fetch(args, webhook_url, translator=None, skip_notify=False):
    """Handle --fetch command: fetch articles and optionally send notifications.
    
    Args:
        args: Command line arguments.
        webhook_url: The webhook URL for notifications.
        translator: Optional translator for translating content.
        skip_notify: If True, skip sending notifications (used when --notify is also specified).
    """
    fetcher = get_fetcher_for_source(args.source)
    query = "cat:cs.LG" if args.source == "arxiv" else ""
    
    # Pass days parameter for date filtering (only for arxiv)
    days = getattr(args, 'days', None)
    if args.source == "arxiv" and days is not None:
        articles = fetcher.fetch_articles(query, max_results=args.max_results, days=days)
    else:
        articles = fetcher.fetch_articles(query, max_results=args.max_results)

    if not articles:
        print("No articles fetched.")
        if not skip_notify:
            notifiers = resolve_notifiers(args.notifier, webhook_url)
            if notifiers:
                print("Sending reminder notification.")
                broadcast_notifications([], notifiers, webhook_url, translator=translator)
        return

    print(f"Successfully fetched {len(articles)} articles from {args.source}.")

    # Store articles
    storage = JsonStorage()
    ensure_dir(args.json_output)
    storage.save_articles(articles, args.json_output)
    print(f"Articles saved to {args.json_output}")

    # Send notifications only if --notify is not also specified
    if skip_notify:
        return
    
    notifiers = resolve_notifiers(args.notifier, webhook_url)
    if not notifiers:
        return
    
    # Limit the number of articles to notify
    limit = getattr(args, 'limit', 5)
    articles_to_notify = articles[:limit] if limit else articles
    if len(articles) > len(articles_to_notify):
        print(f"Limiting notification to {len(articles_to_notify)} of {len(articles)} articles.")
    
    broadcast_notifications(articles_to_notify, notifiers, webhook_url, translator=translator)


def handle_visualize(args):
    """Handle --visualize command: generate HTML visualization."""
    storage = JsonStorage()
    articles = storage.load_articles(args.json_output)
    
    if not articles:
        print("No articles found. Please run '--fetch' first to fetch articles.")
        return

    ensure_dir(args.output)
    visualizer = ArticleVisualizer()
    visualizer.generate_html(articles, args.output)
    print(f"Visualization generated at {args.output}")


def handle_notify(args, webhook_url, translator=None):
    """Handle --notify command: send notifications for stored articles."""
    if not args.notifier:
        print("Please specify a notification channel with --notifier (telegram, webhook, or all)")
        return

    storage = JsonStorage()
    articles = storage.load_articles(args.json_output)
    
    if not articles:
        print(f"No articles found at {args.json_output}. Please run '--fetch' first.")
        return

    notifiers = resolve_notifiers(args.notifier, webhook_url)
    broadcast_notifications(articles, notifiers, webhook_url, translator=translator)


# ============================================================================
# Main Function
# ============================================================================

def parse_args():
    """Parse command line arguments."""
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
    parser.add_argument('--days', type=int, default=1,
                        help='Only fetch articles from the last N days (default: 1, arxiv only)')
    parser.add_argument('--max-results', type=int, default=50,
                        help='Maximum number of articles to fetch before filtering (default: 50)')
    parser.add_argument('--limit', type=int, default=5,
                        help='Maximum number of articles to notify (default: 5)')
    return parser


def main():
    """Main entry point."""
    parser = parse_args()
    args = parser.parse_args()

    if not (args.fetch or args.visualize or args.notify):
        parser.print_help()
        return

    webhook_url = get_webhook_url(args)
    translator = get_translator()

    if args.fetch:
        # Skip notifications in fetch if --notify is also specified (to avoid duplicate)
        handle_fetch(args, webhook_url, translator=translator, skip_notify=args.notify)

    if args.visualize:
        handle_visualize(args)

    if args.notify:
        handle_notify(args, webhook_url, translator=translator)


if __name__ == "__main__":
    main()
