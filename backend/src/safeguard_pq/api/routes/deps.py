from __future__ import annotations

from fastapi import Request, WebSocket

from ..state import AppState


def core(request: Request) -> AppState:
    return request.app.state.core


def ws_core(ws: WebSocket) -> AppState:
    return ws.app.state.core


def pdf_headers(filename: str) -> dict[str, str]:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    return {"Content-Disposition": f'attachment; filename="{safe}"'}
