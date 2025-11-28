
# ML/DL 信息订阅系统

这是一个用于订阅和追踪机器学习（ML）与深度学习（DL）领域最新信息的系统。系统目前支持从 ArXiv 和 Hacker News 获取最新内容，将其保存为结构化 JSON 文件，并可通过多种渠道发送新文章通知。

## 功能特性

- 从 ArXiv API 爬取指定查询条件的最新论文。
- 从 Hacker News 获取热门资讯，并映射为统一的文章数据结构。
- 解析数据，提取标题、作者、摘要、发布日期、链接等核心信息。
- **自动翻译**：
  - ✅ 支持将标题和摘要翻译成中文
  - ✅ 默认使用免费 Google 翻译
  - ✅ 可选使用 DeepL API（翻译质量更高）
- **多渠道通知支持**：
  - ✅ Telegram Bot 通知
  - ✅ Webhook 通知（支持飞书、钉钉等）
  - ✅ 同时向多个渠道发送通知
- **增量通知**：自动比较新旧文章，只通知新增内容，避免重复推送。
- 将获取的文章列表存储在本地 JSON 文件中。
- 将文章可视化为 HTML 文件，便于浏览。
- **GitHub Actions 自动化**：支持定时自动抓取和通知。

## 安装与运行

1.  **克隆项目**

    ```bash
    git clone <your-repo-url>
    cd LLM-NewsLetter
    ```

2.  **安装依赖**

    项目依赖 `requests` 库。通过 `requirements.txt` 文件来安装：

    ```bash
    python3 -m pip install -r requirements.txt
    ```

3.  **配置翻译功能 (可选)**

    系统默认启用免费的 Google 翻译，无需任何配置即可使用。

    ### 使用免费翻译（默认）
    
    无需配置，系统会自动使用 Google 免费翻译服务。
    
    ```bash
    python3 main.py --fetch --notifier webhook --webhook-url "YOUR_WEBHOOK_URL"
    # 输出: Free Google translation enabled.
    ```

    ### 使用 DeepL 翻译（更高质量）

    如需使用 DeepL 获得更高质量的翻译：

    1. 访问 [DeepL API](https://www.deepl.com/pro-api) 注册账号（免费版每月可翻译 50 万字符）
    2. 在账户设置中获取 API Key
    3. 设置环境变量：
    
    ```bash
    export DEEPL_API_KEY="your-deepl-api-key"
    ```

    ### 禁用翻译

    如不需要翻译功能：

    ```bash
    export USE_FREE_TRANSLATOR=false
    ```

4.  **配置通知渠道 (可选)**

    ### Telegram 通知

    - 在 Telegram 中，与 `@BotFather` 对话，使用 `/newbot` 命令创建一个新的机器人，获取 **Bot Token**。
    - 与你的机器人开始对话，然后访问 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` 获取你的 **Chat ID**。
    - 设置环境变量：
      ```bash
      export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
      export TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
      ```

    ### Webhook 通知（飞书、钉钉等）

    - 在飞书/钉钉群中添加自定义机器人，获取 Webhook URL。
    - 设置环境变量：
      ```bash
      export WEBHOOK_URL="YOUR_WEBHOOK_URL"
      ```

5.  **获取文章与发送通知**

    运行以下命令来获取最新的文章并发送通知：

    ```bash
    # 使用指定的通知渠道
    python3 main.py --fetch --source arxiv --notifier telegram
    python3 main.py --fetch --source hn --json-output output/hn_articles.json --notifier webhook

    # 同时向所有已配置的渠道发送通知
    python3 main.py --fetch --source arxiv --notifier all
    ```

    支持的 `--notifier` 选项：
    - `telegram` - 仅发送到 Telegram
    - `webhook` - 仅发送到 Webhook
    - `all` - 自动检测并发送到所有已配置的渠道

    ### 自定义通知样式与 Markdown

    - `--notify-style` 控制通知的冗长度：
      - `detailed`（默认）：包含摘要及双语内容。
      - `compact`：只保留标题与链接，适合快捷浏览。
    - `--notify-format` 控制消息格式：
      - `text`（默认）：沿用 HTML（Telegram）或纯文本（Webhook）。
      - `markdown`：输出 Markdown 消息，Telegram 会自动切换为 `MarkdownV2`，Webhook 会发送 `msg_type=markdown`，方便接入支持 Markdown 的机器人。

6.  **可视化文章**

    使用 `--visualize` 参数来生成 HTML 可视化文件（默认将结果写入 `output/articles.html`）：

    ```bash
    python3 main.py --visualize --output output/articles.html
    ```

    这会读取 `output/articles.json` 文件并生成一个名为 `output/articles.html` 的 HTML 文件。若需更改 JSON 存储位置，可配合 `--json-output` 参数指定。

## 推送效果示例

启用翻译后，推送消息会同时包含原文和中文翻译：

```
✨ New ML/DL Papers Found! ✨

📄 Attention Is All You Need
📄 注意力机制是你所需要的一切
📝 The dominant sequence transduction models are based on complex recurrent...
📝 主流的序列转换模型基于复杂的循环或卷积神经网络...

📄 BERT: Pre-training of Deep Bidirectional Transformers
📄 BERT：深度双向Transformer的预训练
📝 We introduce a new language representation model called BERT...
📝 我们引入了一种新的语言表示模型BERT...
```

## 环境变量

| 变量 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 可选 | - |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID | 可选 | - |
| `WEBHOOK_URL` | Webhook URL | 可选 | - |
| `DEEPL_API_KEY` | DeepL API Key（高质量翻译） | 可选 | - |
| `USE_FREE_TRANSLATOR` | 是否使用免费翻译 | 可选 | `true` |

## GitHub Actions 自动化

项目包含 GitHub Actions 工作流，支持每日自动抓取文章并发送通知。

### 配置 Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中配置以下 Secrets：

| Secret | 说明 | 必需 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 可选 |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID | 可选 |
| `WEBHOOK_URL` | Webhook URL | 可选 |
| `DEEPL_API_KEY` | DeepL API Key | 可选 |

配置了哪些渠道，就会向哪些渠道发送通知，互不影响。

### 触发方式

- **定时触发**：每天 UTC 时间 9:00（北京时间 17:00）自动运行
- **手动触发**：在 Actions 页面点击 "Run workflow" 手动执行

## 如何运行测试

项目包含针对核心模块的单元测试。你可以使用 Python 的 `unittest` 模块来运行所有测试：

```bash
python3 -m unittest discover tests
```

## 项目结构

```
. LLM-NewsLetter/
├── .github/
│   └── workflows/
│       └── daily_fetch.yml   # GitHub Actions 工作流
├── ml_subscriber/
│   ├── __init__.py
│   └── core/
│       ├── __init__.py
│       ├── arxiv_fetcher.py  # ArXiv 爬取与解析模块
│       ├── hn_fetcher.py     # Hacker News 获取模块
│       ├── models.py         # Article 数据模型与协议
│       ├── storage.py        # 数据存储模块 (JSON)
│       ├── notification.py   # 通知模块 (Telegram & Webhook)
│       ├── translator.py     # 翻译模块 (DeepL & Google Free)
│       └── visualization.py  # 文章可视化模块
├── tests/
│   ├── __init__.py
│   ├── test_arxiv_fetcher.py # ArxivFetcher 的单元测试
│   ├── test_hn_fetcher.py    # HackerNewsFetcher 的单元测试
│   ├── test_main.py          # 主程序工具函数的单元测试
│   ├── test_notification.py  # 通知模块的单元测试
│   ├── test_translator.py    # 翻译模块的单元测试
│   ├── test_storage.py       # JsonStorage 的单元测试
│   └── test_visualization.py # ArticleVisualizer 的单元测试
├── main.py                   # 主程序入口
├── requirements.txt          # 项目依赖
└── README.md                 # 项目文档
```

## 未来工作

这个 MVP 版本为后续的开发奠定了基础。未来的工作可以包括：

- **继续扩展信息源**：在现有 ArXiv 与 Hacker News 基础上，增加 Twitter、技术博客 RSS 等。
- **实现真正的数据库**：使用如 MongoDB 或 PostgreSQL 替换 JSON 文件存储。
- **完善订阅与通知系统**：
    - ✅ **通过即时通讯工具接收通知** (已通过 Telegram 实现)
    - ✅ **Webhook 通知支持** (已实现，支持飞书、钉钉等)
    - ✅ **多渠道同时通知** (已实现)
    - ✅ **自动翻译** (已实现，支持 DeepL 和免费 Google 翻译)
    - 允许用户通过关键词订阅。
    - 支持更多通知渠道 (如 Slack, Email)。
- **构建用户界面**：开发一个 Web 前端，让用户可以管理自己的订阅。
- **引入 NLP 功能**：实现自动摘要、主题分类、情感分析等高级功能。
