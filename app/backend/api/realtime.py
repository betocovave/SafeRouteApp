import asyncio
from fastapi import WebSocket


class Hub:
    def __init__(self):
        self.clients: dict[str, set[WebSocket]] = {}

    async def send(self, user_id, message):
        for socket in list(self.clients.get(user_id, set())):
            try:
                await asyncio.wait_for(socket.send_json(message), timeout=2)
            except Exception:
                self.clients.get(user_id, set()).discard(socket)

    async def broadcast(self, message):
        await asyncio.gather(*(self.send(user_id, message) for user_id in list(self.clients)))


hub = Hub()
