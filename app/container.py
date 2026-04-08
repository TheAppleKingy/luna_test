from typing import AsyncGenerator

from fastapi import Request
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine
)
from dishka import (
    make_async_container,
    Scope,
    provide,
    Provider
)
from dishka.integrations.fastapi import (
    FastapiProvider,
    FromDishka
)
from app.infra.configs import (
    DBConfig,
    RabbitConfig,
    AppConfig
)
from app.application.interfaces.services import (
    AuthenticatorServiceInterface,
    WebhookServiceInterface
)
from app.application.interfaces import PublisherInterface
from app.application.interfaces.repositories import (
    PaymentRepositoryInterface,
    OutboxRepositoryInterface
)
from app.infra.services import (
    SafetyAuthenticatorService,
    BackgroundWebhookService
)
from app.application.interactors import (
    CreatePayment,
    ShowPaymentInfo,
    Authenticate,
    ProcessPayment,
    SendMessages
)
from app.application.interfaces import UoWInterface
from app.infra import (
    RabbitPublisher,
    AlchemyUoW
)
from app.infra.repositories import (
    AlchemyOutboxRepository,
    AlchemyPaymentRepository
)
from app.domain.types import Authenticated


class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def db_conf(self) -> DBConfig:
        return DBConfig()  # type: ignore

    @provide
    def rabbit_conf(self) -> RabbitConfig:
        return RabbitConfig()  # type: ignore[call-arg]

    @provide
    def app_conf(self) -> AppConfig:
        return AppConfig()  # type: ignore[call-arg]


class DBProvider(Provider):
    scope = Scope.APP

    @provide
    def engine(self, config: DBConfig) -> AsyncEngine:
        return create_async_engine(config.conn_url)

    @provide
    def get_sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            engine,
            expire_on_commit=False,
            autoflush=False,
            autobegin=False
        )

    @provide(scope=Scope.REQUEST)
    def uow(self, session: AsyncSession) -> UoWInterface:
        return AlchemyUoW(session)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self,
        sessionmaker: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, None]:
        async with sessionmaker() as session:
            try:
                yield session
            finally:
                await session.close()


class BrokerProvider(Provider):
    scope = Scope.APP

    @provide
    async def broker(self, conf: RabbitConfig) -> RabbitBroker:
        broker = RabbitBroker(conf.conn_url)
        return broker

    @provide
    async def publisher(self, broker: RabbitBroker, conf: RabbitConfig) -> PublisherInterface:
        return RabbitPublisher(conf.queue_name, broker)


class RepositoryProvider(Provider):
    scope = Scope.REQUEST

    outbox = provide(AlchemyOutboxRepository, provides=OutboxRepositoryInterface)
    payments = provide(AlchemyPaymentRepository, provides=PaymentRepositoryInterface)


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def authenticator(self, conf: AppConfig) -> AuthenticatorServiceInterface:
        return SafetyAuthenticatorService(conf.api_key)

    @provide
    def webhook_service(self) -> WebhookServiceInterface:
        return BackgroundWebhookService()


class AuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def authenticate(self, r: Request, interactor: FromDishka[Authenticate]) -> Authenticated:
        return Authenticated(interactor(r.headers.get("X-API-Key")))


class InteractorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def send_messages(
        self,
        conf: AppConfig,
        uow: UoWInterface,
        repo: OutboxRepositoryInterface,
        publisher: PublisherInterface
    ) -> SendMessages:
        return SendMessages(
            uow,
            conf.outbox_send_limit,
            repo,
            publisher
        )


interactor_provider = InteractorProvider()
interactor_provider.provide_all(
    CreatePayment,
    ProcessPayment,
    Authenticate,
    ShowPaymentInfo,
)

container = make_async_container(
    interactor_provider,
    RepositoryProvider(),
    AuthProvider(),
    ConfigProvider(),
    ServiceProvider(),
    DBProvider(),
    BrokerProvider(),
    FastapiProvider()
)
