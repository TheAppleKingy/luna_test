import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.application.interactors import SendMessages
from app.domain.entities import Outbox
from app.application.interfaces import UoWInterface, PublisherInterface
from app.application.interfaces.repositories import OutboxRepositoryInterface


@pytest.fixture
def uow_mock():
    uow = AsyncMock(spec=UoWInterface)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.add = Mock()
    uow.commit = AsyncMock()
    return uow


@pytest.fixture
def outbox_repo_mock():
    repo = AsyncMock(spec=OutboxRepositoryInterface)
    repo.get_to_send = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def publisher_mock():
    publisher = AsyncMock(spec=PublisherInterface)
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def send_messages_interactor(uow_mock, outbox_repo_mock, publisher_mock):
    return SendMessages(uow_mock, 10, outbox_repo_mock, publisher_mock)


@pytest.fixture
def sample_outbox():
    payment_id = uuid4()
    outbox = Outbox(payment_id=payment_id)
    outbox.id = 1
    return outbox


class TestSendMessages:
    @pytest.mark.asyncio
    async def test_should_send_messages_and_mark_as_sent(
        self, send_messages_interactor, outbox_repo_mock, publisher_mock, uow_mock, sample_outbox
    ):
        # Arrange
        outboxes = [sample_outbox]
        outbox_repo_mock.get_to_send.return_value = outboxes

        # Act
        result = await send_messages_interactor()

        # Assert
        assert result == 1

        outbox_repo_mock.get_to_send.assert_called_once_with(10)
        publisher_mock.publish.assert_called_once_with(sample_outbox)
        assert sample_outbox.sent_at is not None
        uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_multiple_messages(
        self, send_messages_interactor, outbox_repo_mock, publisher_mock, uow_mock
    ):
        # Arrange
        outbox1 = Outbox(payment_id=uuid4())
        outbox1.id = 1
        outbox2 = Outbox(payment_id=uuid4())
        outbox2.id = 2
        outbox3 = Outbox(payment_id=uuid4())
        outbox3.id = 3

        outboxes = [outbox1, outbox2, outbox3]
        outbox_repo_mock.get_to_send.return_value = outboxes

        # Act
        result = await send_messages_interactor()

        # Assert
        assert result == 3
        assert publisher_mock.publish.call_count == 3
        assert outbox1.sent_at is not None
        assert outbox2.sent_at is not None
        assert outbox3.sent_at is not None
        uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_zero_when_no_messages_to_send(
        self, send_messages_interactor, outbox_repo_mock, publisher_mock, uow_mock
    ):
        # Arrange
        outbox_repo_mock.get_to_send.return_value = []

        # Act
        result = await send_messages_interactor()

        # Assert
        assert result == 0
        outbox_repo_mock.get_to_send.assert_called_once_with(10)
        publisher_mock.publish.assert_not_called()
        uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_respect_send_limit(
        self, send_messages_interactor, outbox_repo_mock, publisher_mock, uow_mock
    ):
        # Arrange
        outboxes = []
        for i in range(15):
            outbox = Outbox(payment_id=uuid4())
            outbox.id = i + 1
            outboxes.append(outbox)

        outbox_repo_mock.get_to_send.return_value = outboxes[:10]  # репозиторий возвращает только 10

        # Act
        result = await send_messages_interactor()

        # Assert
        assert result == 10
        outbox_repo_mock.get_to_send.assert_called_once_with(10)
        assert publisher_mock.publish.call_count == 10

    @pytest.mark.asyncio
    async def test_should_not_send_if_publish_fails(
        self, send_messages_interactor, outbox_repo_mock, publisher_mock, uow_mock, sample_outbox
    ):
        # Arrange
        outboxes = [sample_outbox]
        outbox_repo_mock.get_to_send.return_value = outboxes
        publisher_mock.publish.side_effect = Exception("Broker connection failed")

        # Act & Assert
        with pytest.raises(Exception, match="Broker connection failed"):
            await send_messages_interactor()

        assert sample_outbox.sent_at is None
        uow_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_commit_even_when_no_messages(
        self, send_messages_interactor, outbox_repo_mock, uow_mock
    ):
        # Arrange
        outbox_repo_mock.get_to_send.return_value = []

        # Act
        result = await send_messages_interactor()

        # Assert
        assert result == 0
        uow_mock.__aexit__.assert_called_once()
