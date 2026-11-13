# syntax=docker/dockerfile:1
# ---- Etapa 1: construccion de dependencias ----
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /w
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt

# ---- Etapa 2: imagen final (WeasyPrint necesita pango/harfbuzz y fuentes) ----
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 shared-mime-info fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 sicom
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
RUN mkdir -p /app/storage && chown -R sicom /app
USER sicom
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=10 CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/v1/salud')"
# Migra el esquema y levanta la API. Los datos demo se cargan con: python -m app.seeds (ver docker-compose.yml, perfil "seed")
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
