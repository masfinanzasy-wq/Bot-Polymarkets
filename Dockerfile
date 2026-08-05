# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para asyncpg y compilaciones
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para aprovechar el cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Instalar runtime mínimo para asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias compiladas desde el builder
COPY --from=builder /install /usr/local

# Copiar código fuente del bot
COPY app/ ./app/
COPY .env.example ./.env.example

# Crear directorios de trabajo en runtime
RUN mkdir -p logs data

# Variables de entorno de Python para producción
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    ENVIRONMENT=production

# Usuario no privilegiado para mayor seguridad
RUN useradd --no-create-home --shell /bin/false botuser \
    && chown -R botuser:botuser /app
USER botuser

# Punto de entrada del bot
CMD ["python", "-m", "app.main"]
