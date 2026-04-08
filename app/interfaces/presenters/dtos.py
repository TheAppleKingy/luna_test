import uuid

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domain.entities import (
    Status,
    Currency
)


class ProcessPaymentDTO(BaseModel):
    payment_id: uuid.UUID


class CreatedPaymentInfoDTO(BaseModel):
    id: uuid.UUID
    status: Status
    created_at: datetime


class PaymentInfoDTO(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    meta: dict
    idempotency_key: str
    webhook_url: str
    status: Status
    created_at: datetime
    updated_at: datetime
