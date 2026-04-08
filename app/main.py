import asyncio

from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    APIRouter,
    Request
)
from fastapi.responses import JSONResponse
from faststream.rabbit import (
    RabbitBroker,
    RabbitExchange,
    RabbitQueue
)
from dishka.integrations.fastapi import setup_dishka as fastapi_setup
from dishka.integrations.faststream import setup_dishka as faststream_setup
from sqlalchemy.orm import registry

from app.container import container
from app.domain.entities import (
    Payment,
    Outbox
)
from app.domain.err import HandlingError
from app.infra.db.tables import (
    outbox,
    payments
)
from app.infra.configs import RabbitConfig
from app.interfaces.controllers.broker import broker_router
from app.interfaces.controllers.http import http_router
from app.application.interactors import SendMessages
from app.logger import logger


def map_tables():
    mapper_registry = registry()
    mapper_registry.map_imperatively(Outbox, outbox)
    mapper_registry.map_imperatively(Payment, payments)
    mapper_registry.configure()


event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_fastapi_routers(app)
    broker = await container.get(RabbitBroker)
    broker.include_router(broker_router)
    faststream_setup(container, broker=broker, auto_inject=True)
    await broker.start()
    await set_dead_letter_policy(broker)
    yield
    event.set()
    await broker.stop()
    await container.close()


async def outbox_task():
    while True:
        async with container() as scoped:
            interactor = await scoped.get(SendMessages)
        count = await interactor()
        logger.info(f"{count} messages was sent")
        try:
            await asyncio.wait_for(event.wait(), 10)
            logger.warning("App is shutdown. Checking for deliveries ended")
            return
        except TimeoutError:
            pass


def setup_fastapi_routers(app: FastAPI):
    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(http_router)
    app.include_router(api_router)


async def set_dead_letter_policy(broker: RabbitBroker):
    config = await container.get(RabbitConfig)
    dlx = await broker.declare_exchange(RabbitExchange(f"{config.queue_name}.dlx", durable=True))
    dlq = await broker.declare_queue(RabbitQueue(f"{config.queue_name}.dlq", durable=True))
    await dlq.bind(dlx, routing_key=dlq.name)

map_tables()
app = FastAPI(lifespan=lifespan)
fastapi_setup(container, app)
asyncio.create_task(outbox_task())


@app.exception_handler(HandlingError)
async def handle_auth(r: Request, e: HandlingError):
    return JSONResponse({"detail": str(e)}, e.status)
