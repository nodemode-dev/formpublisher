import asyncio
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import __version__
from app.services.bus import bus

router = APIRouter(tags=["live"])


@router.websocket("/api/live")
async def live(ws: WebSocket):
    await ws.accept()
    bus.attach(asyncio.get_running_loop())
    queue = bus.subscribe()
    await ws.send_json({"type": "hello", "app": "formpublisher", "version": __version__, "at": time.time()})

    async def pump_out():
        while True:
            await ws.send_json(await queue.get())

    async def pump_in():
        while True:
            text = await ws.receive_text()
            if text.strip() in ("ping", '{"type":"ping"}'):
                await ws.send_json({"type": "pong", "at": time.time()})

    sender = asyncio.create_task(pump_out())
    receiver = asyncio.create_task(pump_in())
    try:
        await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for task in (sender, receiver):
            task.cancel()
        bus.unsubscribe(queue)
