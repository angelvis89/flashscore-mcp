# Dockerfile para Flashscore MCP en la nube (Hugging Face Spaces / Fly.io).
# Imagen base oficial de Playwright con Python y Chromium ya instalado.
# Esto evita gigabytes de descarga de browsers en cada deploy.
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MCP_TRANSPORT=streamable-http \
    MCP_BIND_HOST=0.0.0.0 \
    MCP_BIND_PORT=8000 \
    FLASHSCORE_TIMEOUT_MS=22000 \
    FLASHSCORE_MAX_CONCURRENT_PAGES=8 \
    FLASHSCORE_FAST_PARALLEL_SECTIONS=3 \
    FLASHSCORE_HEADLESS=true \
    FLASHSCORE_FULL_DETAIL_TIMEOUT_S=38

# Usuario no-root (HF Spaces lo exige).
RUN useradd -ms /bin/bash mcpuser
WORKDIR /app

# Instalar dependencias primero para cachear capas.
COPY pyproject.toml ./
COPY src ./src
COPY README.md ./

RUN pip install --upgrade pip setuptools wheel && \
    pip install . && \
    chown -R mcpuser:mcpuser /app

USER mcpuser

EXPOSE 8000

# Healthcheck nativo de Docker (HF lo ignora pero Fly.io lo usa).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

# El entry point usa el script de FastMCP. El puerto se toma de MCP_BIND_PORT.
CMD ["python", "-m", "flashscore_mcp.server"]
