from typing import Self, Optional

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction
from app.application.interfaces import UoWInterface


class AlchemyUoW(UoWInterface):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._t: Optional[AsyncSessionTransaction] = None

    async def __aenter__(self) -> Self:
        self._t = await self._session.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._t:
            if exc_type is not None:
                await self._t.rollback()
            else:
                await self._t.commit()
        self._t = None
        return False

    def add(self, *ents):
        return self._session.add_all(ents)
