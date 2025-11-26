
# ML/DL 信息订阅系统

这是一个用于订阅和追踪机器学习（ML）与深度学习（DL）领域最新信息的系统。当前版本可以从 ArXiv 上获取最新的研究论文，并将其保存为结构化的 JSON 文件，同时通过 Telegram 发送新文章通知。

## 功能特性

- 从 ArXiv API 爬取指定查询条件的最新论文。
- 解析论文的 XML 数据，提取标题、作者、摘要、发布日期和 PDF 链接。
- **通过 Telegram Bot 发送新文章的即时通知**。
- 将爬取并解析后的文章列表存储在本地的 JSON 文件中。
- 将爬取到的文章可视化为 HTML 文件。

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

3.  **配置 Telegram 通知 (可选)**

    - 在 Telegram 中，与 `@BotFather` 对话，使用 `/newbot` 命令创建一个新的机器人，获取 **Bot Token**。
    - 与你的机器人开始对话，然后访问 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` 获取你的 **Chat ID**。
    - 在终端中设置环境变量：
      ```bash
      export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
      export TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
      ```

4.  **获取文章与发送通知**

    运行以下命令来获取最新的文章。如果配置了 Telegram，它会自动发送新文章的通知。

    ```bash
    python3 main.py --fetch
    ```

5.  **可视化文章**

    使用 `--visualize` 参数来生成 HTML 可视化文件：

    ```bash
    python3 main.py --visualize --output articles.html
    ```

    这会读取 `articles.json` 文件并生成一个名为 `articles.html` 的 HTML 文件。


## 如何运行测试

项目包含针对核心模块的单元测试。你可以使用 Python 的 `unittest` 模块来运行所有测试：

```bash
python3 -m unittest discover tests
```

## 项目结构

```
. LLM-NewsLetter/
├── ml_subscriber/
│   ├── __init__.py
│   └── core/
│       ├── __init__.py
│       ├── arxiv_fetcher.py  # ArXiv 爬取与解析模块
│       ├── storage.py        # 数据存储模块 (JSON)
│       ├── notification.py   # Telegram 通知模块
│       └── visualization.py  # 文章可视化模块
├── tests/
│   ├── __init__.py
│   ├── test_arxiv_fetcher.py # ArxivFetcher 的单元测试
│   ├── test_storage.py     # JsonStorage 的单元测试
│   ├── test_notification.py  # TelegramNotifier 的单元测试
│   └── test_visualization.py # ArticleVisualizer 的单元测试
├── main.py                   # 主程序入口
├── requirements.txt          # 项目依赖
└── README.md                 # 项目文档
```

## 未来工作

这个 MVP 版本为后续的开发奠定了基础。未来的工作可以包括：

- **增加更多信息源**：如 Hacker News、Twitter、技术博客 RSS 等。
- **实现真正的数据库**：使用如 MongoDB 或 PostgreSQL 替换 JSON 文件存储。
- **完善订阅与通知系统**：
    - ✅ **通过即时通讯工具接收通知** (已通过 Telegram 实现)
    - 允许用户通过关键词订阅。
    - 支持更多通知渠道 (如 Slack, Email)。
- **构建用户界面**：开发一个 Web 前端，让用户可以管理自己的订阅。
- **引入 NLP 功能**：实现自动摘要、主题分类、情感分析等高级功能。

