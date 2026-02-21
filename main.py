
import argparse
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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


def build_fetch_request(args):
    """Build search query and fetch kwargs from CLI arguments."""
    query = "cat:cs.LG" if args.source == "arxiv" else ""
    fetch_kwargs = {"max_results": args.max_results}
    days = getattr(args, "days", None)
    if args.source == "arxiv" and days is not None:
        fetch_kwargs["days"] = days
    return query, fetch_kwargs


def fetch_articles_for_args(args):
    """Fetch articles based on source-specific CLI arguments."""
    fetcher = get_fetcher_for_source(args.source)
    query, fetch_kwargs = build_fetch_request(args)
    return fetcher.fetch_articles(query, **fetch_kwargs)


def notify_no_articles_if_needed(
    args,
    webhook_url,
    translator=None,
    skip_notify=False,
    notify_style="detailed",
    message_format="text",
):
    """Send a reminder when no articles are fetched and notifications are enabled."""
    if skip_notify:
        return
    notifiers = resolve_notifiers(args.notifier, webhook_url)
    if notifiers:
        logger.info("Sending reminder notification.")
        kwargs = {"translator": translator}
        if notify_style != "detailed":
            kwargs["style"] = notify_style
        if message_format != "text":
            kwargs["message_format"] = message_format
        broadcast_notifications([], notifiers, webhook_url, **kwargs)


def save_articles_to_json(articles, json_output):
    """Persist fetched articles to JSON storage."""
    storage = JsonStorage()
    ensure_dir(json_output)
    storage.save_articles(articles, json_output)
    logger.info(f"Articles saved to {json_output}")


def limit_articles_for_notification(articles, limit):
    """Apply notification limit while preserving existing CLI semantics."""
    articles_to_notify = articles[:limit] if limit is not None else articles
    if limit is not None and len(articles) > len(articles_to_notify):
        logger.info(
            f"Limiting notification to {len(articles_to_notify)} of {len(articles)} articles."
        )
    return articles_to_notify


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
        logger.info("DeepL translation enabled.")
        return create_translator(deepl_api_key=deepl_api_key)
    elif use_free:
        logger.info("Free Google translation enabled.")
        return create_translator(use_free=True)
    return create_translator(use_free=False)


def create_notifier(
    notifier_type,
    webhook_url,
    translator=None,
    style="detailed",
    message_format="text",
):
    """Create a notifier instance for the given type."""
    if notifier_type == "telegram":
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            logger.warning("Telegram credentials not found in environment variables.")
            return None
        return TelegramNotifier(
            bot_token,
            chat_id,
            translator=translator,
            style=style,
            message_format=message_format,
        )
    
    if notifier_type == "webhook":
        if not webhook_url:
            logger.warning("Webhook URL not provided.")
            return None
        try:
            return WebhookNotifier(
                webhook_url,
                translator=translator,
                style=style,
                message_format=message_format,
            )
        except ValueError as exc:
            logger.exception("Webhook URL not supported: %s", exc)
            return None
    
    logger.warning(f"Unknown notifier type: {notifier_type}")
    return None


def send_notification(
    articles,
    notifier_type,
    webhook_url,
    translator=None,
    style="detailed",
    message_format="text",
):
    """Send a single notification."""
    notifier = create_notifier(
        notifier_type,
        webhook_url,
        translator=translator,
        style=style,
        message_format=message_format,
    )
    if not notifier:
        return
    
    status = "Sending notification" if articles else "No new articles. Sending reminder"
    logger.info(f"{status} via {notifier_type}...")
    notifier.send(articles)
    logger.info("Notification sent.")


def broadcast_notifications(
    articles,
    notifier_types,
    webhook_url,
    translator=None,
    style="detailed",
    message_format="text",
):
    """Broadcast notifications to multiple channels."""
    if not notifier_types:
        logger.warning("No notification channels configured.")
        return
    
    for notifier_type in notifier_types:
        # Keep backward-compatible call shape when defaults are used.
        kwargs = {"translator": translator}
        if style != "detailed":
            kwargs["style"] = style
        if message_format != "text":
            kwargs["message_format"] = message_format
        send_notification(articles, notifier_type, webhook_url, **kwargs)


# ============================================================================
# Command Handlers
# ============================================================================

def handle_fetch(
    args,
    webhook_url,
    translator=None,
    skip_notify=False,
    notify_style="detailed",
    message_format="text",
):
    """Handle --fetch command: fetch articles and optionally send notifications.
    
    Args:
        args: Command line arguments.
        webhook_url: The webhook URL for notifications.
        translator: Optional translator for translating content.
        skip_notify: If True, skip sending notifications (used when --notify is also specified).
    """
    articles = fetch_articles_for_args(args)

    if not articles:
        logger.info("No articles fetched.")
        notify_no_articles_if_needed(
            args,
            webhook_url,
            translator=translator,
            skip_notify=skip_notify,
            notify_style=notify_style,
            message_format=message_format,
        )
        return

    logger.info(f"Successfully fetched {len(articles)} articles from {args.source}.")

    # Store articles
    save_articles_to_json(articles, args.json_output)

    # Send notifications only if --notify is not also specified
    if skip_notify:
        return
    
    notifiers = resolve_notifiers(args.notifier, webhook_url)
    if not notifiers:
        return
    
    # Limit the number of articles to notify
    limit = getattr(args, 'limit', 5)
    articles_to_notify = limit_articles_for_notification(articles, limit)
    
    kwargs = {"translator": translator}
    if notify_style != "detailed":
        kwargs["style"] = notify_style
    if message_format != "text":
        kwargs["message_format"] = message_format
    broadcast_notifications(articles_to_notify, notifiers, webhook_url, **kwargs)


def handle_visualize(args):
    """Handle --visualize command: generate HTML visualization."""
    storage = JsonStorage()
    articles = storage.load_articles(args.json_output)
    
    if not articles:
        logger.warning("No articles found. Please run '--fetch' first to fetch articles.")
        return

    ensure_dir(args.output)
    visualizer = ArticleVisualizer()
    visualizer.generate_html(articles, args.output)
    logger.info(f"Visualization generated at {args.output}")


def handle_notify(
    args,
    webhook_url,
    translator=None,
    notify_style="detailed",
    message_format="text",
):
    """Handle --notify command: send notifications for stored articles."""
    if not args.notifier:
        logger.warning("Please specify a notification channel with --notifier (telegram, webhook, or all)")
        return

    storage = JsonStorage()
    articles = storage.load_articles(args.json_output)
    
    if not articles:
        logger.warning(f"No articles found at {args.json_output}. Please run '--fetch' first.")
        return

    notifiers = resolve_notifiers(args.notifier, webhook_url)
    kwargs = {"translator": translator}
    if notify_style != "detailed":
        kwargs["style"] = notify_style
    if message_format != "text":
        kwargs["message_format"] = message_format
    broadcast_notifications(articles, notifiers, webhook_url, **kwargs)


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
    parser.add_argument('--notify-style', type=str, choices=['detailed', 'compact'], default='detailed',
                        help='Notification verbosity. "compact" omits summaries.')
    parser.add_argument('--notify-format', type=str, choices=['text', 'markdown'], default='text',
                        help='Output format. "markdown" enables Markdown (Telegram MarkdownV2 / Webhook Markdown-ish).')
    return parser


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = parse_args()
    args = parser.parse_args()

    if not (args.fetch or args.visualize or args.notify):
        parser.print_help()
        return

    webhook_url = get_webhook_url(args)
    translator = get_translator()
    notify_style = getattr(args, "notify_style", "detailed")
    notify_format = getattr(args, "notify_format", "text")

    if args.fetch:
        # Skip notifications in fetch if --notify is also specified (to avoid duplicate)
        handle_fetch(
            args,
            webhook_url,
            translator=translator,
            skip_notify=args.notify,
            notify_style=notify_style,
            message_format=notify_format,
        )

    if args.visualize:
        handle_visualize(args)

    if args.notify:
        handle_notify(
            args,
            webhook_url,
            translator=translator,
            notify_style=notify_style,
            message_format=notify_format,
        )


if __name__ == "__main__":
    main()
