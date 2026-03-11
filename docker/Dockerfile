# Dockerfile para FastAPI (backend)
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (cache de dependencias)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo do backend
COPY backend/ ./backend/

# Expor porta
EXPOSE 3000

# Variaveis de ambiente padrao
ENV PORT=3000
ENV HOST=0.0.0.0

# Comando para iniciar
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "3000"]
