"""
Cache-Aside con Redis para pets-service.

Incluye:
- Circuit breaker manual en memoria (5 errores / 10 s → bypass 30 s).
- Singleflight vía SETNX para evitar cache stampede.
- Graceful degradation: si Redis falla, se ejecuta la función directamente.
"""

import inspect
import json
import logging
import os
import threading
import time
from functools import wraps
from typing import Any, Callable, Optional

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


def _cache_enabled() -> bool:
    return os.getenv("CACHE_ENABLED", "true").lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


class _CircuitBreaker:
    """Circuit breaker thread-safe en memoria."""

    def __init__(
        self,
        error_threshold: int = 5,
        window_seconds: int = 10,
        open_duration_seconds: int = 30,
    ) -> None:
        self.error_threshold = error_threshold
        self.window_seconds = window_seconds
        self.open_duration_seconds = open_duration_seconds
        self._errors: list[float] = []
        self._open_until: Optional[float] = None
        self._lock = threading.Lock()

    def record_error(self) -> None:
        now = time.time()
        with self._lock:
            self._errors.append(now)
            cutoff = now - self.window_seconds
            self._errors = [t for t in self._errors if t > cutoff]
            if len(self._errors) >= self.error_threshold:
                self._open_until = now + self.open_duration_seconds
                logger.warning(
                    "Circuit breaker OPEN — Redis bypassed until %.0f",
                    self._open_until,
                )

    def is_open(self) -> bool:
        with self._lock:
            if self._open_until is not None:
                if time.time() < self._open_until:
                    return True
                self._open_until = None
            cutoff = time.time() - self.window_seconds
            self._errors = [t for t in self._errors if t > cutoff]
            return False


_circuit_breaker = _CircuitBreaker()


def _is_redis_error(e: Exception) -> bool:
    return isinstance(e, (redis.ConnectionError, redis.TimeoutError, redis.RedisError))


def _get_redis_client() -> Optional[redis.Redis]:
    try:
        return redis.from_url(
            REDIS_URL,
            socket_timeout=0.2,
            socket_connect_timeout=0.2,
            health_check_interval=30,
        )
    except Exception as e:
        logger.warning("Failed to create Redis client: %s", e)
        return None


def _serialize_item(value: Any) -> Any:
    """Convierte recursivamente objetos Pydantic a dicts."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_serialize_item(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_item(v) for k, v in value.items()}
    return value


def _serialize(value: Any) -> str:
    return json.dumps(_serialize_item(value), default=str)


def _deserialize(data: bytes) -> Any:
    return json.loads(data)


def cached(ttl_seconds: int, key_fn: Callable):
    """Decorador cache-aside con singleflight y graceful degradation."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _cache_enabled():
                return func(*args, **kwargs)

            if _circuit_breaker.is_open():
                return func(*args, **kwargs)

            client = _get_redis_client()
            if client is None:
                return func(*args, **kwargs)

            cache_key = key_fn(*args, **kwargs)
            lock_key = f"{cache_key}:lock"

            # 1) Intentar leer de cache
            try:
                cached_data = client.get(cache_key)
                if cached_data is not None:
                    return _deserialize(cached_data)
            except Exception as e:
                if _is_redis_error(e):
                    _circuit_breaker.record_error()
                logger.warning("Redis read error for key %s: %s", cache_key, e)
                return func(*args, **kwargs)

            # 2) Cache miss — intentar adquirir lock
            acquired = False
            try:
                acquired = client.set(lock_key, "1", nx=True, ex=2)
            except Exception as e:
                if _is_redis_error(e):
                    _circuit_breaker.record_error()
                logger.warning("Redis lock error for key %s: %s", lock_key, e)
                return func(*args, **kwargs)

            if acquired:
                try:
                    result = func(*args, **kwargs)
                    try:
                        client.setex(cache_key, ttl_seconds, _serialize(result))
                    except Exception as e:
                        if _is_redis_error(e):
                            _circuit_breaker.record_error()
                        logger.warning(
                            "Redis write error for key %s: %s", cache_key, e
                        )
                    return result
                except Exception:
                    # Si la función falla, liberar el lock para que otro lo intente
                    try:
                        client.delete(lock_key)
                    except Exception:
                        pass
                    raise

            # 3) No se adquirió el lock — esperar y reintentar leer
            for _ in range(10):
                time.sleep(0.05)
                try:
                    cached_data = client.get(cache_key)
                    if cached_data is not None:
                        return _deserialize(cached_data)
                except Exception as e:
                    if _is_redis_error(e):
                        _circuit_breaker.record_error()
                    logger.warning(
                        "Redis read retry error for key %s: %s", cache_key, e
                    )
                    return func(*args, **kwargs)

            # 4) Si después de 2 s nadie escribió, ejecutar directamente
            return func(*args, **kwargs)

        # Preservar firma para FastAPI/OpenAPI
        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str) -> None:
    """Elimina todas las claves que coincidan con el patrón dado."""
    client = _get_redis_client()
    if client is None:
        return
    try:
        keys = list(client.scan_iter(match=pattern))
        if keys:
            client.delete(*keys)
            logger.info(
                "Invalidated %d keys matching pattern %s", len(keys), pattern
            )
    except Exception as e:
        if _is_redis_error(e):
            _circuit_breaker.record_error()
        logger.warning("Redis invalidate error for pattern %s: %s", pattern, e)
