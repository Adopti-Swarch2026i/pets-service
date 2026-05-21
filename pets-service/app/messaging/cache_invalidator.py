"""
Consumer RabbitMQ para invalidación de cache.

Escucha los eventos pet.report.* y borra las entradas de Redis
afectadas (single-item + listas).
"""

import json
import logging
import os
import ssl
import threading
import time
from typing import Optional

import pika

from app.cache import _circuit_breaker, _get_redis_client, _is_redis_error

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "adopti.events"
ROUTING_KEYS = [
    "pet.report.created",
    "pet.report.updated",
    "pet.report.reunited",
    "pet.report.deleted",
]

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqps://adopti:__RABBITMQ_PASSWORD__@localhost:5671/",
)


class CacheInvalidator:
    def __init__(self) -> None:
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _connect(self) -> Optional[str]:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            params.heartbeat = 600
            params.blocked_connection_timeout = 300
            if RABBITMQ_URL.startswith("amqps://"):
                ssl_context = ssl.create_default_context(cafile="/app/certs/ca.crt")
                params.ssl_options = pika.SSLOptions(ssl_context)
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type="topic",
                durable=True,
            )
            result = self._channel.queue_declare(
                queue="", exclusive=True, auto_delete=True
            )
            queue_name = result.method.queue
            for rk in ROUTING_KEYS:
                self._channel.queue_bind(
                    queue=queue_name,
                    exchange=EXCHANGE_NAME,
                    routing_key=rk,
                )
            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._on_message,
                auto_ack=True,
            )
            logger.info(
                "Cache invalidator consumer started on queue %s", queue_name
            )
            return queue_name
        except Exception as e:
            logger.exception("Failed to start cache invalidator: %s", e)
            return None

    def _on_message(
        self,
        ch: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.frame.Method,
        properties: pika.BasicProperties,
        body: bytes,
    ) -> None:
        try:
            payload = json.loads(body)
            report_id = payload.get("reportId") or payload.get("petId")
            if report_id is None:
                return

            client = _get_redis_client()
            if client is None:
                return

            try:
                client.delete(f"pets:id:{report_id}")
                list_keys = list(client.scan_iter(match="pets:list:*"))
                if list_keys:
                    client.delete(*list_keys)
                logger.info(
                    "Invalidated cache for report %s via %s",
                    report_id,
                    method.routing_key,
                )
            except Exception as e:
                if _is_redis_error(e):
                    _circuit_breaker.record_error()
                logger.warning("Redis invalidation error: %s", e)
        except Exception:
            logger.exception("Error processing cache invalidation message")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                queue_name = self._connect()
                if queue_name is None:
                    time.sleep(5)
                    continue
                while (
                    self._connection
                    and self._connection.is_open
                    and not self._stop_event.is_set()
                ):
                    self._connection.process_data_events(time_limit=1)
            except Exception as e:
                logger.warning("Cache invalidator connection error: %s", e)
                time.sleep(5)
            finally:
                if self._connection and self._connection.is_open:
                    try:
                        self._connection.close()
                    except Exception:
                        pass

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Cache invalidator thread started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._connection and self._connection.is_open:
            try:
                self._connection.add_callback_threadsafe(self._connection.close)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)


_invalidator: Optional[CacheInvalidator] = None


def start_cache_invalidator() -> None:
    global _invalidator
    if _invalidator is None:
        _invalidator = CacheInvalidator()
        _invalidator.start()


def stop_cache_invalidator() -> None:
    global _invalidator
    if _invalidator is not None:
        _invalidator.stop()
        _invalidator = None
