import asyncio
import json
import logging
from contextlib import AsyncExitStack
from dataclasses import asdict
from typing import Optional, List, Union

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function
from openai.types.shared_params.function_definition import FunctionDefinition

# Application-specific configs (import your dataclasses from config.py)
from config import LLMClientConfig, LLMRequestConfig, MCPClientConfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class MCPClient:
    def __init__(
        self,
        mcp_config: MCPClientConfig = MCPClientConfig(),
        llm_config: LLMClientConfig = LLMClientConfig(),
        request_config: LLMRequestConfig = LLMRequestConfig(model="gpt-4o")
    ):
        self.mcp_config = mcp_config
        self.llm_config = llm_config
        self.request_config = request_config
        # Filter out any None values (so we only pass api_key + organization if set)
        llm_params = {k: v for k, v in asdict(self.llm_config).items() if v is not None}
        self.llm = AsyncOpenAI(**llm_params)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self, server_name: str):
        """Establish stdio connection to an MCP server."""
        cfg = self.mcp_config.mcpServers.get(server_name)
        if not cfg or not cfg.enabled:
            raise ValueError(f"Server '{server_name}' not available or disabled.")

        # Split command into executable + args
        raw_cmd = cfg.command
        cmd_args = cfg.args or []
        if not cmd_args and isinstance(raw_cmd, str) and " " in raw_cmd.strip():
            parts = raw_cmd.strip().split()
            raw_cmd = parts[0]
            cmd_args = parts[1:]

        params = StdioServerParameters(
            command=raw_cmd,
            args=cmd_args,
            env=cfg.env,
            cwd=cfg.cwd,
        )

        # Open stdio client
        reader, writer = await self.exit_stack.enter_async_context(
            stdio_client(params)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(reader, writer)
        )
        await self.session.initialize()

        tools = (await self.session.list_tools()).tools
        logging.info("Connected to '%s', available tools: %s", server_name, [t.name for t in tools])

    async def _call_tool(self, tool_call) -> ChatCompletionToolMessageParam:
        """Execute a tool call via MCP and wrap the result."""
        if tool_call.type != "function":
            raise ValueError(f"Unsupported tool call type: {tool_call.type}")
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        res = await self.session.call_tool(name, args)  # type: ignore
        if res.isError:
            raise RuntimeError(f"Tool '{name}' error: {res.content}")

        output = [c.text for c in res.content if c.type == "text"]
        return ChatCompletionToolMessageParam(
            role="tool",
            content=json.dumps({"tool": name, "output": output}),
            tool_call_id=tool_call.id,
        )

    async def chat(
        self,
        messages: List[Union[dict, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam]]
    ) -> List[Union[dict, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam]]:
        """Recursively send messages to the LLM, handling tool invocations."""
        if not self.session:
            raise RuntimeError("Not connected to a server.")

        # Build tool definitions
        tools = [
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=tool.inputSchema,
                ),
            )
            for tool in (await self.session.list_tools()).tools
        ]

        resp = await self.llm.chat.completions.create(
            messages=messages,
            tools=tools,
            tool_choice="auto",
            **asdict(self.request_config),
        )
        choice = resp.choices[0]
        reason = choice.finish_reason

        # Handle completion
        if reason == "stop":
            messages.append({"role": "assistant", "content": choice.message.content})
            return messages

        if reason == "tool_calls":
            calls = choice.message.tool_calls or []
            # Append placeholder for tool calls – `content` is REQUIRED
            messages.append({
                "role": "assistant",
                "content": None,          # ← important for OpenAI schema
                "tool_calls": [
                    {
                        "id": c.id,
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments
                        },
                        "type": c.type
                    }
                    for c in calls
                ]
            })
            # Execute tools
            results = await asyncio.gather(*[self._call_tool(c) for c in calls])
            messages.extend(results)
            return await self.chat(messages)

        raise RuntimeError(f"Unhandled finish_reason: {reason}")

    async def close(self):
        """Clean up resources and ignore close-time errors."""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            logging.warning("Error during client close: %s", e)

async def main():
    client = MCPClient()
    await client.connect("default")     # Bunq server (incl. web-search tool)

    # Initial conversation history with a comprehensive Financial-Advisor prompt
    history = [
        {
            "role": "system",
            "content": (
                "You are FinCoach, a seasoned **independent financial advisor** for "
                "upper-middle-class clients in the Netherlands.  \n\n"
                "You have secure, real-time access to the client's Bunq data and "
                "the following MCP tools:\n"
                "• get_accounts, get_account_balance, get_transactions  \n"
                "• make_payment, request_payment  \n"
                "• get_cards, block_card, unblock_card  \n"
                "• personal_information, income_expenses, assets_liabilities  \n"
                "• financial_goals, risk_profile, tax_situation  \n"
                "• legal_estate_planning, preferences_values  \n"
                "• financial_statement_last_5_years  \n"
                "• search (web search for external facts & prices)  \n\n"
                "Guidelines:\n"
                "1. Start every new session with a short personalised greeting.  \n"
                "2. Politely ask clarifying questions **before** giving advice if "
                "information is missing.  \n"
                "3. Proactively call the relevant tools to gather data; show results "
                "only when they add value.  \n"
                "4. Think step-by-step, then provide clear, actionable "
                "recommendations – reference concrete numbers from the tools.  \n"
                "5. Use *Markdown* formatting (headings, bullet lists, tables, code "
                "blocks for JSON) so that the UI can render beautifully.  \n"
                "6. If you cite external facts (inflation, tax rules, prices, etc.) "
                "use the **search** tool first and cite the source URL.  \n"
                "7. Finish with a concise summary and a friendly call-to-action.  \n\n"
                "_Compliance_: This is educational information and not formal "
                "investment advice. Remind the user that personal circumstances may "
                "require tailored professional advice."
            ),
        },
        {"role": "user", "content": "Show all my accounts and their balance"},
    ]

    conversation = await client.chat(history)
    for msg in conversation:
        # Handle both dicts and param objects
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")
        else:
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", None)
        if role == "assistant":
            print("Assistant:", content)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())