# Multi-Stage Production Dockerfile for ACP (Agent Collaboration Protocol) Node
FROM python:3.13-slim as builder

WORKDIR /build
RUN pip install --upgrade pip build
COPY . .
RUN python -m build

FROM python:3.13-slim

WORKDIR /app
COPY --from=builder /build/dist/*.whl /app/
RUN pip install --no-cache-dir /app/*.whl

EXPOSE 8080 50051
ENTRYPOINT ["python3", "-m", "acp.cli.main", "inspect-mesh"]
