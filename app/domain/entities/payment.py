import uuid

from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass, field


class Currency(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class Status(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeded"
    FAILED = "failed"


@dataclass
class Payment:
    amount: Decimal
    currency: Currency
    description: str
    meta: dict
    idempotency_key: str
    webhook_url: str
    id: uuid.UUID = field(default_factory=uuid.uuid7, init=False)
    status: Status = field(default_factory=lambda: Status.PENDING, init=False)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), init=False)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), init=False)
