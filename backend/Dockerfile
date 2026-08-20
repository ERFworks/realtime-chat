FROM python:3.13-slim

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /app \
       --shell /usr/sbin/nologin app \
    && mkdir -p /app && chown app:app /app

WORKDIR /app

RUN pip install --no-cache-dir uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HOME=/app

COPY --chown=app:app pyproject.toml uv.lock ./

USER app

RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app . .

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
