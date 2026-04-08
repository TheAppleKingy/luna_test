from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl

from app.domain.entities import Currency


class CreatePaymentDTO(BaseModel):
    amount: Decimal = Field(ge=0)
    currency: Currency
    description: str = Field(max_length=500)
    meta: dict
    webhook_url: HttpUrl
