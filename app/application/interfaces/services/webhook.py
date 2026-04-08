from typing import Protocol


class WebhookServiceInterface(Protocol):
    async def send(self, data: dict, url: str): ...
