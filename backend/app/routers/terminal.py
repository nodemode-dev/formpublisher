import asyncio
import json
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services import agent_programs, paths, terminal, window_key

router = APIRouter(prefix="/api/terminal", tags=["terminal"])
RESUME = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,199}\Z")
PERSON_ONLY = "Terminal tabs belong to the person: an agent's tab key cannot open, change or attach them."


class OpenBody(BaseModel):
    kind: Literal["shell", "claude", "codex", "cursor", "antigravity"] = "shell"
    cols: int = 100
    rows: int = 30
    prompt: str | None = Field(None, max_length=100_000)
    resume: str | None = Field(None, max_length=200)


class SizeBody(BaseModel):
    cols: int
    rows: int


def _person(request: Request) -> None:
    if not window_key.personal(request.headers.get(window_key.HEADER)):
        raise HTTPException(status_code=403, detail=PERSON_ONLY)


def _session(sid: str) -> terminal.Session:
    try:
        return terminal.get(sid)
    except KeyError:
        raise HTTPException(status_code=404, detail="There is no such terminal.")


def _no_pty() -> JSONResponse:
    return JSONResponse({"detail": "This system cannot make a terminal (no PTY is available to the engine).", "code": "no-pty"}, status_code=503)


@router.get("")
def list_terminals() -> dict:
    kinds = (["shell"] if terminal.available() else []) + (agent_programs.runnable_kinds() if terminal.available() else [])
    return {"version": terminal.VERSION, "available": kinds, "terminals": terminal.listing()}


@router.post("")
def open_terminal(body: OpenBody, request: Request):
    _person(request)
    if not terminal.available():
        return _no_pty()
    cols, rows = terminal.clamp(body.cols, body.rows)
    if body.resume is not None and (body.kind != "claude" or not RESUME.match(body.resume)):
        raise ValueError("resume must be a Claude Code session id (letters, digits, - and _) and is only for kind claude")
    try:
        if body.kind == "shell":
            return terminal.open_shell(cols, rows).describe()
        return agent_programs.open_agent(body.kind, cols, rows, body.prompt or None, body.resume or None)
    except agent_programs.NotInstalled as exc:
        return JSONResponse({"detail": str(exc), "code": "not-installed"}, status_code=404)
    except RuntimeError as exc:
        if str(exc) == "no-pty":
            return _no_pty()
        raise
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"The program could not start: {exc}")


@router.post("/{sid}/restart")
def restart_terminal(sid: str, request: Request) -> dict:
    _person(request)
    _session(sid)
    try:
        return terminal.restart(sid).describe()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"The program could not start again: {exc}")


@router.delete("/{sid}")
def close_terminal(sid: str, request: Request) -> dict:
    _person(request)
    terminal.close(sid)
    return {"ok": True}


@router.post("/{sid}/resize")
def resize_terminal(sid: str, body: SizeBody, request: Request) -> dict:
    _person(request)
    _session(sid)
    terminal.resize(sid, body.cols, body.rows)
    return {"ok": True}


@router.post("/{sid}/ticket")
def ticket(sid: str, request: Request) -> dict:
    _person(request)
    _session(sid)
    return {"ticket": terminal.buy_ticket(sid)}


def _exit_frame(code) -> bytes:
    return json.dumps({"type": "exit", "code": code}).encode("utf-8")


@router.websocket("/{sid}/stream")
async def stream(ws: WebSocket, sid: str, ticket: str = "") -> None:
    origin = ws.headers.get("origin")
    await ws.accept()
    if (origin is not None and origin.rstrip("/") not in paths.origins()) or not terminal.spend_ticket(ticket, sid):
        await ws.close(code=4403)
        return
    session = terminal.SESSIONS.get(sid)
    if session is None:
        await ws.close(code=4404)
        return
    queue: asyncio.Queue = asyncio.Queue()
    backlog, mark = session.snapshot()
    session.subscribers.add(queue)

    async def outbound() -> None:
        await ws.send_text(backlog)
        if not session.alive:
            await ws.send_bytes(_exit_frame(session.code))
        while True:
            message = await queue.get()
            if message[0] == "data":
                if message[1] > mark:
                    await ws.send_text(message[2])
            elif message[0] == "exit":
                await ws.send_bytes(_exit_frame(message[1]))
            elif message[0] == "reset":
                await ws.send_text("\x1bc")
            elif message[0] == "closed":
                return

    async def inbound() -> None:
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                return
            text = message.get("text")
            if not text:
                continue
            try:
                data = json.loads(text)
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("type") == "input" and isinstance(data.get("data"), str):
                await asyncio.to_thread(terminal.write, sid, data["data"])
            elif data.get("type") == "resize":
                try:
                    terminal.resize(sid, int(data.get("cols")), int(data.get("rows")))
                except (TypeError, ValueError, KeyError):
                    continue

    tasks = {asyncio.create_task(outbound()), asyncio.create_task(inbound())}
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        session.subscribers.discard(queue)
    for task in tasks:
        if task.done() and not task.cancelled():
            task.exception()
    try:
        await ws.close()
    except Exception:
        pass
