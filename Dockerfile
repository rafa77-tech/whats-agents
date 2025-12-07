# Dockerfile multi-stage para Agente Júlia
FROM python:3.13-slim AS builder

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

WORKDIR /app

# Copiar arquivos de dependências
COPY pyproject.toml uv.lock ./

# Instalar dependências
RUN uv sync --frozen --no-dev

# Stage final
FROM python:3.13-slim

WORKDIR /app

# Instalar dependências mínimas do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar uv e ambiente virtual do builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copiar código da aplicação
COPY app/ ./app/
COPY static/ ./static/
COPY migrations/ ./migrations/

# Criar diretório de logs
RUN mkdir -p /app/logs

# Variáveis de ambiente
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Comando padrão (pode ser sobrescrito)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

