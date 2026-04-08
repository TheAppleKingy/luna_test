import uuid

from typing import Optional

from app.domain.entities import Payment


class PaymentRepositoryInterface:
    async def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]: ...
    async def get_by_idempotency_key(self, key: str) -> Optional[Payment]: ...
