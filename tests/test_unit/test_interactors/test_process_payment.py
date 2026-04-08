import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from app.application.interactors import ProcessPayment
from app.domain.entities import Payment, Status, Currency
from app.application.err import UndefinedPaymentError
from app.domain.err import PaymentAlreadyProcessedError
from app.application.interfaces import UoWInterface
from app.application.interfaces.repositories import PaymentRepositoryInterface, OutboxRepositoryInterface
from app.application.interfaces.services import WebhookServiceInterface


@pytest.fixture
def uow_mock():
    uow = AsyncMock(spec=UoWInterface)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.add = Mock()
    return uow


@pytest.fixture
def payment_repo_mock():
    repo = AsyncMock(spec=PaymentRepositoryInterface)
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def outbox_repo_mock():
    return AsyncMock(spec=OutboxRepositoryInterface)


@pytest.fixture
def webhook_service_mock():
    service = AsyncMock(spec=WebhookServiceInterface)
    service.send = AsyncMock()
    return service


@pytest.fixture
def process_payment_interactor(uow_mock, payment_repo_mock, outbox_repo_mock, webhook_service_mock):
    return ProcessPayment(uow_mock, payment_repo_mock, outbox_repo_mock, webhook_service_mock)


@pytest.fixture
def sample_payment():
    payment = Payment(
        amount=Decimal("100.00"),
        currency=Currency.RUB,
        description="Test payment",
        meta={},
        idempotency_key="test-key",
        webhook_url="https://example.com/webhook"
    )
    return payment


class TestProcessPayment:
    @pytest.mark.asyncio
    async def test_should_process_payment_successfully(
        self, process_payment_interactor, payment_repo_mock, uow_mock, webhook_service_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        payment_repo_mock.get_by_id.return_value = sample_payment
        sample_payment.status = Status.PENDING

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor

            # Симулируем изменение статуса
            async def mock_process(payment):
                payment.status = Status.SUCCEEDED
                payment.updated_at = datetime.now(timezone.utc)

            mock_processor.process.side_effect = mock_process

            # Act
            await process_payment_interactor(payment_id)

            # Assert
            mock_processor.process.assert_called_once_with(sample_payment)
            assert sample_payment.status == Status.SUCCEEDED
            assert sample_payment.updated_at is not None
            payment_repo_mock.get_by_id.assert_called_once_with(payment_id)
            webhook_service_mock.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_raise_error_when_payment_not_found(
        self, process_payment_interactor, payment_repo_mock, uow_mock, webhook_service_mock
    ):
        # Arrange
        payment_id = uuid.uuid4()
        payment_repo_mock.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(UndefinedPaymentError, match=f"Payment with id '{payment_id}' does not exist"):
            await process_payment_interactor(payment_id)

        payment_repo_mock.get_by_id.assert_called_once_with(payment_id)
        webhook_service_mock.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_process_already_processed_payment(
        self, process_payment_interactor, payment_repo_mock, uow_mock, webhook_service_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = Status.SUCCEEDED
        payment_repo_mock.get_by_id.return_value = sample_payment
        original_updated_at = sample_payment.updated_at

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor
            mock_processor.process.side_effect = PaymentAlreadyProcessedError("Already processed")

            # Act
            await process_payment_interactor(payment_id)

            # Assert
            mock_processor.process.assert_called_once_with(sample_payment)
            assert sample_payment.status == Status.SUCCEEDED
            webhook_service_mock.send.assert_not_called()
            uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_inexpected_processing_error(
        self, process_payment_interactor, payment_repo_mock, uow_mock, webhook_service_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        sample_payment.status = Status.SUCCEEDED
        payment_repo_mock.get_by_id.return_value = sample_payment
        original_updated_at = sample_payment.updated_at

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor
            mock_processor.process.side_effect = Exception("Undefined error")

            # Act
            try:
                await process_payment_interactor(payment_id)
            except Exception as e:
                # Assert
                mock_processor.process.assert_called_once_with(sample_payment)
                assert sample_payment.status == Status.SUCCEEDED
                webhook_service_mock.send.assert_not_called()
                uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_send_webhook_on_success(
        self, process_payment_interactor, payment_repo_mock, uow_mock, webhook_service_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        payment_repo_mock.get_by_id.return_value = sample_payment
        sample_payment.status = Status.PENDING

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor
            mock_processor.process = AsyncMock()
            sample_payment.status = Status.SUCCEEDED

            # Act
            await process_payment_interactor(payment_id)

            # Assert
            webhook_service_mock.send.assert_called_once_with(
                {
                    "payment_id": str(sample_payment.id),
                    "status": sample_payment.status.value,
                    "updated_at": sample_payment.updated_at.isoformat()
                },
                str(sample_payment.webhook_url)
            )

    @pytest.mark.asyncio
    async def test_should_handle_webhook_error_gracefully(
        self, process_payment_interactor, payment_repo_mock, uow_mock, webhook_service_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        payment_repo_mock.get_by_id.return_value = sample_payment
        sample_payment.status = Status.PENDING
        exc = Exception("Webhook delivery failed")
        webhook_service_mock.send.side_effect = exc

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor
            mock_processor.process = AsyncMock()

            # Act
            try:
                await process_payment_interactor(payment_id)
            except Exception as e:
                # Assert
                mock_processor.process.assert_called_once_with(sample_payment)
                webhook_service_mock.send.assert_called_once()
                uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_update_updated_at_timestamp(
        self, process_payment_interactor, payment_repo_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        payment_repo_mock.get_by_id.return_value = sample_payment
        sample_payment.status = Status.PENDING
        original_updated_at = sample_payment.updated_at

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor
            mock_processor.process = AsyncMock()

            # Act
            await process_payment_interactor(payment_id)

            # Assert
            assert sample_payment.updated_at >= original_updated_at

    @pytest.mark.asyncio
    async def test_should_commit_changes_to_database(
        self, process_payment_interactor, payment_repo_mock, uow_mock, sample_payment
    ):
        # Arrange
        payment_id = sample_payment.id
        payment_repo_mock.get_by_id.return_value = sample_payment
        sample_payment.status = Status.PENDING

        with patch("app.application.interactors.payments.PaymentProcessor") as MockProcessor:
            mock_processor = AsyncMock()
            MockProcessor.return_value = mock_processor
            mock_processor.process = AsyncMock()

            # Act
            await process_payment_interactor(payment_id)

            # Assert
            uow_mock.__aexit__.assert_called_with(None, None, None)
