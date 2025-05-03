"""
Simple web chat service that wraps your MCPClient.
Run with:
    uvicorn chat_web.app:app --reload
"""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from bunq_mcp_client import MCPClient          # <-- existing code is reused

# ------------------------------------------------------------------
# FastAPI initialisation
# ------------------------------------------------------------------
app = FastAPI(title="Bunq-MCP Chat")

# MCP connection is created once and shared by all requests
client = MCPClient()
_client_lock = asyncio.Lock()                  # serialise access to the MCP session


@app.on_event("startup")
async def _startup() -> None:
    await client.connect("default")


@app.on_event("shutdown")
async def _shutdown() -> None:
    await client.close()


# ------------------------------------------------------------------
# Helper for (de)serialising OpenAI chat objects
# ------------------------------------------------------------------
def _msg_to_dict(m: Union[dict, Any]) -> Dict[str, Any]:
    """Convert OpenAI / custom objects back to plain dicts for JSON response."""
    if isinstance(m, dict):
        return m
    # OpenAI objects inherit from pydantic.BaseModel → prefer model_dump
    if hasattr(m, "model_dump"):
        return m.model_dump(exclude_none=True)
    if hasattr(m, "dict"):
        return m.dict(exclude_none=True)  # type: ignore
    # fallback – last resort
    return json.loads(str(m))


# ------------------------------------------------------------------
# API schema
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    messages: List[dict]


class ChatResponse(BaseModel):
    messages: List[dict]


# ------------------------------------------------------------------
# REST endpoint
# ------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # NOTE: For a production service you might keep a client per user
    async with _client_lock:
        try:
            print(f"Processing chat request with {len(req.messages)} messages")
            conv = await client.chat(req.messages)
            print(f"Successfully processed chat request, received {len(conv)} messages in response")
        except Exception as exc:
            import traceback
            error_traceback = traceback.format_exc()
            error_type = type(exc).__name__
            error_details = {
                "error_type": error_type,
                "error_message": str(exc),
                "traceback": error_traceback,
                "request_messages_count": len(req.messages),
            }
            print(f"ERROR in chat endpoint: {error_type}: {str(exc)}")
            print(f"Detailed error info: {json.dumps(error_details, indent=2)}")
            print(f"Traceback:\n{error_traceback}")
            raise HTTPException(500, f"{error_type}: {str(exc)}") from exc

    return ChatResponse(messages=[_msg_to_dict(m) for m in conv])


# ------------------------------------------------------------------
# User-info endpoint – forwards the MCP "get_user_info" tool
# ------------------------------------------------------------------
@app.get("/user_info")
async def user_info() -> dict:
    """
    Fetch user information via the `get_user_info` tool exposed by the MCP
    server and return it as plain JSON so the front-end can personalise
    greetings (name, etc.).
    """
    if not client.session:
        raise HTTPException(503, "MCP session not ready")

    async with _client_lock:
        try:
            result = await client.session.call_tool("get_user_info", {})  # type: ignore
            if result.isError:
                raise RuntimeError(result.content)

            # The tool returns a JSON string; decode it back to dict
            text = next((c.text for c in result.content if c.type == "text"), "{}")
            return json.loads(text)
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc


# ------------------------------------------------------------------
# Very tiny HTML/JS front-end
# ------------------------------------------------------------------
_HTML = (Path(__file__).parent / "index.html").read_text()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _HTML 