FROM python:3.13-alpine

LABEL org.opencontainers.image.description="Simple Proxmox TUI Manager"
LABEL org.opencontainers.image.source=https://github.com/benzino77/lazyprox
LABEL org.opencontainers.image.licenses=MIT

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN addgroup --system lazyprox && adduser --system --ingroup lazyprox lazyprox

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

RUN uv sync --frozen --compile-bytecode --no-dev && \
    chown -R lazyprox:lazyprox /app

ENV PATH="/app/.venv/bin:$PATH"

USER lazyprox

ENTRYPOINT ["lazyprox"]
