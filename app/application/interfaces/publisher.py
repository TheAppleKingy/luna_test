from typing import Protocol

from app.domain.entities import Outbox


class PublisherInterface(Protocol):
    async def publish(self, outbox: Outbox) -> None: ...
