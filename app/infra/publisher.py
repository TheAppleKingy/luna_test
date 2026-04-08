import json


from faststream.rabbit import RabbitBroker
from app.application.interfaces import PublisherInterface
from app.domain.entities import Outbox


class RabbitPublisher(PublisherInterface):
    def __init__(
        self,
        queue_name: str,
        broker: RabbitBroker
    ):

        self._queue_name = queue_name
        self._broker = broker

    async def publish(self, outbox: Outbox):
        await self._broker.publish(
            json.dumps({"payment_id": outbox.payment_id}, default=str).encode(),
            persist=True,
            queue=self._queue_name
        )
