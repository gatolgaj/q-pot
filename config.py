import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict

# -----------------------------------------------------------------------------
# Configuration dataclasses for Bunq MCP Async Client
# -----------------------------------------------------------------------------

@dataclass
class LLMClientConfig:
    """
    Configuration for the OpenAI client.
    Fields map directly to AsyncOpenAI init parameters.
    """
    api_key: str = "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"
    base_url: Optional[str] = None
    timeout: Optional[float] = None


@dataclass
class LLMRequestConfig:
    """
    Parameters for LLM chat completion requests.
    """
    model: str = "gpt-4o"
    temperature: float = 0.7
    top_p: float = 1.0
    n: int = 1
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop: Optional[List[str]] = None
    user: Optional[str] = None
    logit_bias: Optional[Dict[str, int]] = None


@dataclass
class MCPServerConfig:
    """
    Configuration for a single MCP server (stdio transport).
    Fields must match mcp.client.stdio.StdioServerParameters.
    """
    enabled: bool = True
    command: str = os.getenv("MCP_SERVER_COMMAND", "/Users/ssvk/.pyenv/shims/uv run /Users/ssvk/Documents/GitHub/bunqhack/bunq_mcp_server.py")
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None


@dataclass
class MCPClientConfig:
    """
    Holds all MCP server configurations by name.
    """
    mcpServers: dict = field(
        default_factory=lambda: {
            "default": MCPServerConfig()
        }
    )
