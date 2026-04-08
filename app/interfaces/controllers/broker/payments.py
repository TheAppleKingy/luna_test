from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt
)
from faststream.rabbit import (
    RabbitRouter,
    RabbitQueue
)
from dishka.integrations.faststream import FromDishka

from app.interfaces.presenters.dtos import ProcessPaymentDTO
from app.application.interactors import ProcessPayment
broker_router = RabbitRouter()


@broker_router.subscriber(RabbitQueue("payments.new", durable=True, arguments={
    "x-dead-letter-exchange": "payments.new.dlx",
    "x-dead-letter-routing-key": "payments.new.dlq"
}))
async def process_payment(
    dto: ProcessPaymentDTO,
    interactor: FromDishka[ProcessPayment],
):
    await _process_with_retry(dto, interactor)


@retry(
    wait=wait_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
    reraise=True
)
async def _process_with_retry(dto: ProcessPaymentDTO, interactor: ProcessPayment):
    await interactor(dto.payment_id)
