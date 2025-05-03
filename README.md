# Q-pot 💶🤖

AI-powered  financial coach for Bunq users.  
Ask anything about your spending, goals, mortgage or investments; FinCoach will:

1. Call Bunq-style MCP tools to fetch data (mock tools in this repo)  
2. Do a web search when it needs external facts (DuckDuckGo)  
3. Reply with clear, Markdown-formatted advice in a modern chat UI

Everything (UI ➜ FastAPI gateway ➜ MCP client ➜ MCP server) ships in one Docker image, so you can run it locally or deploy to any container host.

---

## Features

| Layer / File                     | Tech / Purpose                                                                 |
|----------------------------------|--------------------------------------------------------------------------------|
| `chat_web/index.html`            | Static SPA (vanilla JS), Font Awesome icons, scrollable chat                    |
| `chat_web/app.py`                | FastAPI server: serves UI, `/chat` & `/user_info` endpoints                     |
| `bunq_mcp_client.py`             | Bridges OpenAI Chat API ↔ MCP servers, handles tool-calls                      |
| `bunq_mcp_server.py`             | Mock Bunq tools, web-search, mortgage & portfolio tools                        |
| Dockerfile                       | Slim Python 3.12 image; runs `uvicorn chat_web.app:app` on port `8000`          |

### Built-in MCP tools (mock data)

* Banking: `get_accounts`, `get_account_balance`, `get_transactions`, …  
* **`search`** – TLS-tolerant DuckDuckGo search  
* **`mortgage_account_transactions`** – recent payments & interest rate  
* **`investment_portfolio`** – holdings, value & performance snapshot  

Add your own tools by decorating an `async` function in `bunq_mcp_server.py` with `@mcp.tool()`.

---

## Quick Start (local)
