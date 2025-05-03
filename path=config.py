from dataclasses import dataclass, field
import os
from typing import Optional, Union, List

@dataclass
class LLMClientConfig:
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    organization: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_ORGANIZATION"))
    # … any other fields you already have (e.g. base_url, timeout, etc.) 

@dataclass
class MCPServerEntry:
    command: Union[str, List[str]]
    args: List[str] | None = None
    env: dict | None = None
    cwd: str | None = None
    enabled: bool = True

@dataclass
class MCPClientConfig:
    mcpServers: dict = field(
        default_factory=lambda: {
            # existing Bunq tooling
            "default": MCPServerEntry(command="python bunq_mcp_server.py"),
            # NEW: google-search server
            "search":  MCPServerEntry(command="python google_search_mcp_server.py"),
        }
    ) 