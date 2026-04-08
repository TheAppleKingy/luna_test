import asyncio
import httpx

from app.application.interfaces.services import WebhookServiceInterface


class BackgroundWebhookService(WebhookServiceInterface):
    async def send(self, data: dict, url: str):
        async def _send_task():
            try:
                cli = httpx.AsyncClient()
                await cli.post(url=url, json=data)
            except:  # noqa: E722
                pass
        asyncio.create_task(_send_task())
