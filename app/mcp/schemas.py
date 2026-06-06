from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JsonRpcRequest(BaseModel):
    jsonrpc: str
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None
