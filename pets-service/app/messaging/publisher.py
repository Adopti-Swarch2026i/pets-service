"""
RabbitMQ event publisher for pets-service.

Publishes domain events to the 'adopti.events' topic exchange so other
services (notification, matching) can react.

Convención (sección 7.3 de p2_plan.md):
  - El payload del mensaje es directamente el `data` del evento (no un
    envelope), para que los consumers puedan deserializar al schema del
    contrato sin desempacar.
  - `eventId` (UUID v4) y `eventTimestamp` (ISO 8601) viajan en los
    headers AMQP, no en el body.
  - `eventId` también se duplica en `message_id` y `eventTimestamp` en
    `timestamp` para herramientas que inspeccionan propiedades estándar.
"""

import json
import logging
import os
import re
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import pika

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "adopti.events"


def _sanitize_url(url: str) -> str:
    """Remove credentials from a URL before logging."""
    if not url:
        return url
    # Replace user:password@ with user:***REDACTED***@
    return re.sub(r"(://)([^:]+):([^@]+)@", r"\1\2:***REDACTED***@", url)


def _sanitize_error_message(message: str) -> str:
    """Sanitize any error message that might contain URLs with credentials."""
    if not message:
        return message
    return _sanitize_url(message)


class EventPublisher:
    """Synchronous RabbitMQ publisher (pika)."""

    def __init__(self) -> None:
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def connect(self) -> None:
        url = os.getenv(
            "RABBITMQ_URL",
            "amqp://adopti:rabbitmq_secret@localhost:5672/",
        )
        try:
            params = pika.URLParameters(url)
            params.heartbeat = 600
            params.blocked_connection_timeout = 300
            if url.startswith("amqps://"):
                ssl_context = ssl.create_default_context(cafile="/app/certs/ca.crt")
                params.ssl_options = pika.SSLOptions(ssl_context)
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type="topic",
                durable=True,
            )
            logger.info("Connected to RabbitMQ; exchange '%s' declared", EXCHANGE_NAME)
        except Exception as e:
            logger.exception(
                "Failed to connect to RabbitMQ: %s",
                _sanitize_error_message(str(e)),
            )
            self._connection = None
            self._channel = None

    def publish(self, routing_key: str, payload: Dict[str, Any]) -> None:
        if self._channel is None or self._connection is None or self._connection.is_closed:
            self.connect()

        if self._channel is None:
            logger.warning("RabbitMQ unavailable — dropping event %s", routing_key)
            return

        event_id = str(uuid4())
        now = datetime.now(timezone.utc)
        event_timestamp = now.isoformat()

        properties = pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type="application/json",
            content_encoding="utf-8",
            message_id=event_id,
            timestamp=int(now.timestamp()),
            headers={
                "eventId": event_id,
                "eventTimestamp": event_timestamp,
            },
        )

        try:
            self._channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=json.dumps(payload, default=str).encode("utf-8"),
                properties=properties,
            )
            logger.info("Published event %s (id=%s)", routing_key, event_id)
        except Exception as e:
            logger.exception(
                "Failed to publish event %s: %s",
                routing_key,
                _sanitize_error_message(str(e)),
            )
            self._connection = None
            self._channel = None

    def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            try:
                self._connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception:
                logger.warning("Error while closing RabbitMQ connection", exc_info=True)


_publisher: Optional[EventPublisher] = None


def get_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
        _publisher.connect()
    return _publisher


def close_publisher() -> None:
    global _publisher
    if _publisher is not None:
        _publisher.close()
        _publisher = None
