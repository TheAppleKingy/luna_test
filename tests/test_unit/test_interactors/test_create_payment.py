import uuid
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.application.interactors import CreatePayment
from app.application.dtos import CreatePaymentDTO
from app.domain.entities import Payment, Outbox, Currency, Status
from app.application.interfaces import UoWInterface
from app.application.interfaces.repositories import PaymentRepositoryInterface


@pytest.fixture
def uow_mock():
    uow = AsyncMock(spec=UoWInterface)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.add = Mock()
    uow.commit = AsyncMock()
    return uow


@pytest.fixture
def payment_repo_mock():
    repo = AsyncMock(spec=PaymentRepositoryInterface)
    repo.get_by_idempotency_key = AsyncMock()
    return repo


@pytest.fixture
def create_payment_interactor(uow_mock, payment_repo_mock):
    return CreatePayment(uow_mock, payment_repo_mock)


class TestCreatePayment:
    @pytest.mark.asyncio
    async def test_should_create_new_payment_when_idempotency_key_not_exists(
        self, create_payment_interactor, payment_repo_mock, uow_mock
    ):
        # Arrange
        idempotency_key = "test-key-123"
        payment_repo_mock.get_by_idempotency_key.return_value = None

        dto = CreatePaymentDTO(
            amount=Decimal("100.50"),
            currency=Currency.RUB,
            description="Test payment",
            meta={"order_id": 123},
            webhook_url="https://example.com/webhook"
        )

        # Act
        result = await create_payment_interactor(idempotency_key, dto)

        # Assert
        assert isinstance(result, Payment)
        assert result.id is not None
        assert isinstance(result.id, uuid.UUID)
        assert result.amount == Decimal("100.50")
        assert result.currency == Currency.RUB
        assert result.description == "Test payment"
        assert result.meta == {"order_id": 123}
        assert result.webhook_url == "https://example.com/webhook"
        assert result.idempotency_key == idempotency_key
        assert result.status == Status.PENDING
        assert result.created_at is not None
        assert result.updated_at is not None

        payment_repo_mock.get_by_idempotency_key.assert_called_once_with(idempotency_key)

        uow_mock.add.assert_called_once()
        args = uow_mock.add.call_args[0]
        assert len(args) == 2
        assert isinstance(args[0], Payment)
        assert isinstance(args[1], Outbox)
        assert args[1].payment_id == args[0].id

    @pytest.mark.asyncio
    async def test_should_return_existing_payment_when_idempotency_key_exists(
        self, create_payment_interactor, payment_repo_mock, uow_mock
    ):
        # Arrange
        idempotency_key = "existing-key"
        existing_payment = Payment(
            amount=Decimal("50.00"),
            currency=Currency.USD,
            description="Existing payment",
            meta={"existing": True},
            idempotency_key=idempotency_key,
            webhook_url="https://example.com/existing"
        )
        payment_repo_mock.get_by_idempotency_key.return_value = existing_payment

        dto = CreatePaymentDTO(
            amount=Decimal("100.50"),
            currency=Currency.RUB,
            description="New payment that should not be created",
            meta={},
            webhook_url="https://example.com/webhook"
        )

        # Act
        result = await create_payment_interactor(idempotency_key, dto)

        # Assert
        assert result is existing_payment
        assert result.idempotency_key == idempotency_key
        assert result.amount == Decimal("50.00")
        assert result.currency == Currency.USD

        payment_repo_mock.get_by_idempotency_key.assert_called_once_with(idempotency_key)
        uow_mock.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_create_payment_with_zero_amount(
        self, create_payment_interactor, payment_repo_mock, uow_mock
    ):
        # Arrange
        idempotency_key = "zero-amount-key"
        payment_repo_mock.get_by_idempotency_key.return_value = None

        dto = CreatePaymentDTO(
            amount=Decimal("0"),
            currency=Currency.RUB,
            description="Zero amount payment",
            meta={},
            webhook_url="https://example.com/webhook"
        )

        # Act
        result = await create_payment_interactor(idempotency_key, dto)

        # Assert
        assert result.amount == Decimal("0")
        assert isinstance(result, Payment)
        uow_mock.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_payment_with_different_currencies(
        self, create_payment_interactor, payment_repo_mock, uow_mock
    ):
        # Arrange
        idempotency_key = "usd-key"
        payment_repo_mock.get_by_idempotency_key.return_value = None

        dto = CreatePaymentDTO(
            amount=Decimal("100.00"),
            currency=Currency.USD,
            description="USD payment",
            meta={},
            webhook_url="https://example.com/webhook"
        )

        # Act
        result = await create_payment_interactor(idempotency_key, dto)

        # Assert
        assert result.currency == Currency.USD
        assert isinstance(result, Payment)
        uow_mock.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_payment_with_meta(
        self, create_payment_interactor, payment_repo_mock, uow_mock
    ):
        # Arrange
        idempotency_key = "meta-key"
        payment_repo_mock.get_by_idempotency_key.return_value = None

        meta = {"customer_id": 12345, "items": [1, 2, 3], "note": "test"}
        dto = CreatePaymentDTO(
            amount=Decimal("75.00"),
            currency=Currency.EUR,
            description="Payment with meta",
            meta=meta,
            webhook_url="https://example.com/webhook"
        )

        # Act
        result = await create_payment_interactor(idempotency_key, dto)

        # Assert
        assert result.meta == meta
        assert isinstance(result, Payment)
        uow_mock.add.assert_called_once()
