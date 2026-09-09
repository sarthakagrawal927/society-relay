FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.9
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY relay ./relay
COPY docs/architecture.svg ./docs/architecture.svg
RUN useradd --uid 10001 --create-home relay && mkdir work && chown relay:relay work
USER relay
ENV PATH="/app/.venv/bin:$PATH" RELAY_MODEL_PROVIDER=gateway
EXPOSE 8000
CMD ["sh", "-c", "uvicorn relay.app:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
