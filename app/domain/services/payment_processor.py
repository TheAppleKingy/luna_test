import random
import asyncio

from datetime import datetime, timezone

from app.domain.entities import (
    Payment,
    Status
)
from app.domain.err import PaymentAlreadyProcessedError


class PaymentProcessor:
    async def process(self, payment: Payment):
        if payment.status != Status.PENDING:
            raise PaymentAlreadyProcessedError(f"Payment '{payment.id}' already processed")
        await asyncio.sleep(random.randint(2, 5))
        if random.randint(1, 10) == 1:
            payment.status = Status.FAILED
        else:
            payment.status = Status.SUCCEEDED
        payment.updated_at = datetime.now(timezone.utc)
