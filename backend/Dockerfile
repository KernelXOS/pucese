FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema: psycopg2 + WeasyPrint (PDF) + polars
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear carpeta para encuestas
RUN mkdir -p /app/encuestas

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
