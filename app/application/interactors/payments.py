import uuid

from app.application.interfaces import (
    UoWInterface,
    PublisherInterface
)
from app.application.dtos import CreatePaymentDTO
from app.domain.entities import (
    Payment,
    Outbox
)
from app.application.interfaces.repositories import (
    OutboxRepositoryInterface,
    PaymentRepositoryInterface
)
from app.application.interfaces.services import WebhookServiceInterface
from app.domain.services import PaymentProcessor
from app.application.err import UndefinedPaymentError
from app.domain.err import PaymentAlreadyProcessedError


class CreatePayment:
    def __init__(
        self,
        uow: UoWInterface,
        payment_repo: PaymentRepositoryInterface
    ):
        self._uow = uow
        self._payment_repo = payment_repo

    async def __call__(self, idempotency_key: str, dto: CreatePaymentDTO) -> Payment:  # type: ignore[return]
        async with self._uow as uow:
            payment = await self._payment_repo.get_by_idempotency_key(idempotency_key)
            if not payment:
                payment = Payment(
                    dto.amount,
                    dto.currency,
                    dto.description,
                    dto.meta,
                    idempotency_key,
                    str(dto.webhook_url)
                )
                outbox = Outbox(payment.id)
                uow.add(payment, outbox)
            return payment


class SendMessages:
    def __init__(
        self,
        uow: UoWInterface,
        send_limit: int,
        outbox_repo: OutboxRepositoryInterface,
        publisher: PublisherInterface
    ):
        self._uow = uow
        self._send_limit = send_limit
        self._outbox_repo = outbox_repo
        self._publisher = publisher

    async def __call__(self) -> int:  # type: ignore[return]
        async with self._uow:
            outboxes = await self._outbox_repo.get_to_send(self._send_limit)
            count = 0
            for outbox in outboxes:
                await self._publisher.publish(outbox)
                outbox.mark_sent()
                count += 1
            return count


class ProcessPayment:
    def __init__(
        self,
        uow: UoWInterface,
        payment_repo: PaymentRepositoryInterface,
        outbox_repo: OutboxRepositoryInterface,
        webhook_service: WebhookServiceInterface
    ):
        self._uow = uow
        self._payment_repo = payment_repo
        self._outbox_repo = outbox_repo
        self._webhook_service = webhook_service

    async def __call__(self, payment_id: uuid.UUID):
        async with self._uow:
            payment = await self._payment_repo.get_by_id(payment_id)
            if not payment:
                raise UndefinedPaymentError(f"Payment with id '{payment_id}' does not exist")
            now_processed = False
            try:
                processor = PaymentProcessor()
                await processor.process(payment)  # type: ignore[arg-type]
                now_processed = True
            except PaymentAlreadyProcessedError:
                pass
        if now_processed:
            await self._webhook_service.send({
                "payment_id": str(payment.id),  # type: ignore[union-attr]
                "status": payment.status.value,  # type: ignore[union-attr]
                "updated_at": payment.updated_at.isoformat()  # type: ignore[union-attr]
            }, str(payment.webhook_url))  # type: ignore[union-attr]


class ShowPaymentInfo:
    def __init__(
        self,
        uow: UoWInterface,
        payment_repo: PaymentRepositoryInterface,
    ):
        self._uow = uow
        self._payment_repo = payment_repo

    async def __call__(self, payment_id: uuid.UUID):
        async with self._uow:
            return await self._payment_repo.get_by_id(payment_id)
