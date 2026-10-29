# syntax=docker/dockerfile:1

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# O banco é SQLite (módulo embutido no Python) e todas as dependências têm wheels:
# não há pacotes de sistema a instalar (libpq/build-essential só seriam necessários com PostgreSQL).

# Instala dependências Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY . .

# Usuário sem privilégios; media/ recebe as fotos enviadas pelos doadores
RUN useradd --create-home app \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Migrations e collectstatic rodam na subida (ver docker-compose.yml): com o volume `.:/app`
# a pasta staticfiles/ gerada no build ficaria oculta.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
