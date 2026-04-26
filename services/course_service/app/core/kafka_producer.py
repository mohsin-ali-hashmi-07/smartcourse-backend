import json
from aiokafka import AIOKafkaProducer
from app.core.settings import settings

_producer: AIOKafkaProducer | None = None

async def start_producer() -> None:
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await _producer.start()

async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None

def get_producer() -> AIOKafkaProducer:
    return _producer