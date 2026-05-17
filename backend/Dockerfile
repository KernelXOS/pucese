FROM python:3.11-slim

WORKDIR /app

# Todas las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    # PostgreSQL
    libpq-dev \
    gcc \
    g++ \
    # WeasyPrint (PDF)
    libcairo2 \
    libcairo-gobject2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    shared-mime-info \
    fonts-liberation \
    # Utilidades
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Puerto dinámico para Railway
ENV PORT=8000
EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
