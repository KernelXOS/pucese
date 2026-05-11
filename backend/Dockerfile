FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para psycopg2 y polars
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear carpeta para encuestas
RUN mkdir -p /app/encuestas

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
