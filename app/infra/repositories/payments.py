import uuid

from typing import Optional

from sqlalchemy import select

from app.domain.entities import Payment
from app.application.interfaces.repositories import PaymentRepositoryInterface
from .base import BaseAlchemyRepository


class AlchemyPaymentRepository(BaseAlchemyRepository, PaymentRepositoryInterface):
    async def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        return await self._session.scalar(select(Payment).where(Payment.id == payment_id))   # type: ignore[arg-type]

    async def get_by_idempotency_key(self, key: str) -> Optional[Payment]:
        return await self._session.scalar(
            select(Payment).where(Payment.idempotency_key == key)  # type: ignore[arg-type]
        )
