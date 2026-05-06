"""Issue #64 — verify every MCP response carries `Connection: close`.

The MCP server wraps the ASGI ``send`` callable in
``_wrap_send_with_close`` so uvicorn closes the TCP socket
(and sends FIN) immediately after each response body. Without
this wrapper, stateless StreamableHTTP responses sat in
keep-alive and accumulated CLOSE_WAIT sockets on the server
side once the hook clients closed first.
"""

from __future__ import annotations

import asyncio

from app.mcp.server import _wrap_send_with_close


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_response_start_gets_connection_close_header():
    captured: list[dict] = []

    async def fake_send(message: dict) -> None:
        captured.append(message)

    wrapped = _wrap_send_with_close(fake_send)

    async def drive() -> None:
        await wrapped({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await wrapped({"type": "http.response.body", "body": b"{}"})

    _run(drive())

    assert len(captured) == 2
    start = captured[0]
    assert start["type"] == "http.response.start"
    headers = dict(start["headers"])
    assert headers.get(b"connection") == b"close"
    assert headers.get(b"content-type") == b"application/json"
    assert captured[1] == {"type": "http.response.body", "body": b"{}"}


def test_existing_connection_header_is_replaced():
    captured: list[dict] = []

    async def fake_send(message: dict) -> None:
        captured.append(message)

    wrapped = _wrap_send_with_close(fake_send)

    async def drive() -> None:
        await wrapped({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"connection", b"keep-alive"),
            ],
        })

    _run(drive())

    headers = captured[0]["headers"]
    connection_values = [v for k, v in headers if k.lower() == b"connection"]
    assert connection_values == [b"close"]


def test_non_response_start_messages_pass_through():
    captured: list[dict] = []

    async def fake_send(message: dict) -> None:
        captured.append(message)

    wrapped = _wrap_send_with_close(fake_send)

    async def drive() -> None:
        await wrapped({"type": "http.disconnect"})
        await wrapped({"type": "http.response.body", "body": b"x"})

    _run(drive())

    assert captured == [
        {"type": "http.disconnect"},
        {"type": "http.response.body", "body": b"x"},
    ]
