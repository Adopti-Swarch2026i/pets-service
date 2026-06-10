"""Service Discovery client for Consul.

Registers this pets-service instance with Consul on startup and deregisters
on shutdown. Uses only the standard library (no extra dependencies).
"""

import json
import logging
import os
import socket
import urllib.request
from urllib.error import URLError

log = logging.getLogger(__name__)

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "pets-service")
SERVICE_ID = os.getenv("SERVICE_ID", f"{SERVICE_NAME}-{socket.gethostname()}")
SERVICE_HOST = os.getenv("SERVICE_HOST", socket.gethostname())
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8443"))


def _consul_url(path: str) -> str:
    return f"http://{CONSUL_HOST}:{CONSUL_PORT}{path}"


def register() -> None:
    payload = {
        "ID": SERVICE_ID,
        "Name": SERVICE_NAME,
        "Address": SERVICE_HOST,
        "Port": SERVICE_PORT,
        "Tags": ["fastapi", "python", "https", "mtls"],
        "Check": {
            "TCP": f"{SERVICE_HOST}:{SERVICE_PORT}",
            "Interval": "10s",
            "Timeout": "5s",
            "DeregisterCriticalServiceAfter": "1m",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _consul_url("/v1/agent/service/register"),
        data=body,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status >= 300:
                log.warning("Consul register returned status=%s", resp.status)
            else:
                log.info("Registered %s with Consul as %s", SERVICE_ID, SERVICE_NAME)
    except URLError as exc:
        log.warning("Failed to register with Consul: %s", exc)


def deregister() -> None:
    req = urllib.request.Request(
        _consul_url(f"/v1/agent/service/deregister/{SERVICE_ID}"),
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            log.info("Deregistered %s from Consul", SERVICE_ID)
    except URLError as exc:
        log.warning("Failed to deregister from Consul: %s", exc)
