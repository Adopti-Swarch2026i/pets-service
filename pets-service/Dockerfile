FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv lock && uv sync --no-dev

COPY ./app ./app

EXPOSE 8443

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8443", "--ssl-keyfile", "/app/certs/server.key", "--ssl-certfile", "/app/certs/server.crt", "--ssl-ca-certs", "/app/certs/ca.crt", "--ssl-cert-reqs", "2"]
