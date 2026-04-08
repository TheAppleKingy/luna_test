from typing import Optional


from sqlalchemy import select, desc

from app.domain.entities import Outbox
from app.application.interfaces.repositories import OutboxRepositoryInterface
from .base import BaseAlchemyRepository


class AlchemyOutboxRepository(BaseAlchemyRepository, OutboxRepositoryInterface):
    async def get_to_send(self, limit: int) -> list[Outbox]:
        res = await self._session.scalars(
            select(Outbox).where(Outbox.sent_at == None).  # type: ignore[arg-type] #noqa: E711
            order_by(desc(Outbox.created_at)).  # type: ignore[arg-type]
            limit(limit)
        )
        return res.all()  # type: ignore[return-value]

    async def get_by_id(self, outbox_id: int) -> Optional[Outbox]:
        return await self._session.scalar(select(Outbox).where(Outbox.id == outbox_id))  # type: ignore[arg-type]
