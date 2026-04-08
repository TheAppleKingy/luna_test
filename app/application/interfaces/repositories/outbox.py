from typing import Protocol, Optional

from app.domain.entities import Outbox


class OutboxRepositoryInterface(Protocol):
    async def get_to_send(self, limit: int) -> list[Outbox]: ...
    async def get_by_id(self, outbox_id: int) -> Optional[Outbox]: ...
