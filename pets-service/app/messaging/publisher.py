"""
RabbitMQ event publisher for pets-service.

Publishes domain events to the 'adopti.events' topic exchange
so that other services (notification, matching) can react.
"""

import json
import os
import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, Optional

import pika

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "adopti.events"


class EventPublisher:
    """Synchronous RabbitMQ publisher using pika."""

    def __init__(self):
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None

    def connect(self):
        url = os.getenv("RABBITMQ_URL", "amqp://adopti:rabbitmq_secret@localhost:5672/")
        try:
            params = pika.URLParameters(url)
            params.heartbeat = 600
            params.blocked_connection_timeout = 300
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type="topic",
                durable=True,
            )
            logger.info("Connected to RabbitMQ and declared exchange '%s'", EXCHANGE_NAME)
        except Exception:
            logger.exception("Failed to connect to RabbitMQ")
            self._connection = None
            self._channel = None

    def publish(self, routing_key: str, payload: Dict[str, Any]):
        if self._channel is None or self._connection is None or self._connection.is_closed:
            self.connect()

        if self._channel is None:
            logger.warning("RabbitMQ unavailable — dropping event %s", routing_key)
            return

        message = {
            "eventId": str(uuid4()),
            "eventTimestamp": datetime.now(timezone.utc).isoformat(),
            "routingKey": routing_key,
            "data": payload,
        }

        try:
            self._channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=json.dumps(message, default=str).encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent
                    content_type="application/json",
                ),
            )
            logger.info("Published event %s (id=%s)", routing_key, message["eventId"])
        except Exception:
            logger.exception("Failed to publish event %s", routing_key)
            self._connection = None
            self._channel = None

    def close(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            logger.info("RabbitMQ connection closed")


# Singleton instance
_publisher: Optional[EventPublisher] = None


def get_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
        _publisher.connect()
    return _publisher


def close_publisher():
    global _publisher
    if _publisher:
        _publisher.close()
        _publisher = None
