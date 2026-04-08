import uuid

from fastapi import (
    APIRouter,
    Header,
    status
)
from dishka.integrations.fastapi import (
    FromDishka,
    DishkaRoute
)

from app.domain.types import Authenticated
from app.application.interactors import (
    CreatePayment,
    ShowPaymentInfo
)
from app.application.dtos import CreatePaymentDTO
from app.interfaces.presenters.dtos import (
    CreatedPaymentInfoDTO,
    PaymentInfoDTO
)

http_router = APIRouter(prefix="/payments", tags=["Payments"], route_class=DishkaRoute)


@http_router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    dto: CreatePaymentDTO,
    interactor: FromDishka[CreatePayment],
    _: FromDishka[Authenticated],
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> CreatedPaymentInfoDTO:
    return await interactor(idempotency_key, dto)  # type: ignore[return-value]


@http_router.get("/{payment_id}")
async def get_payment_info(
    payment_id: uuid.UUID,
    _: FromDishka[Authenticated],
    interactor: FromDishka[ShowPaymentInfo]
) -> PaymentInfoDTO:
    return await interactor(payment_id)
