"""Request-scoped MCP context.

The HTTP transport sets this once per MCP request so project scoping does
not depend on mutable globals or thread-local state.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from app.config import DEFAULT_PROJECT


@dataclass(frozen=True)
class PrismRequestContext:
    project_id: str = DEFAULT_PROJECT
    request_id: str = ""
    transport: str = "mcp-http"
    tool_profile: str = "interactive"


_current_request: ContextVar[PrismRequestContext] = ContextVar(
    "prism_request_context",
    default=PrismRequestContext(),
)


def get_request_context() -> PrismRequestContext:
    """Return the current MCP request context."""
    return _current_request.get()


@contextmanager
def use_request_context(ctx: PrismRequestContext) -> Iterator[PrismRequestContext]:
    """Run a block under a request context and always restore the prior one."""
    token = _current_request.set(ctx)
    try:
        yield ctx
    finally:
        _current_request.reset(token)
