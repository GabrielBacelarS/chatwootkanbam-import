# Dockerfile para FastAPI
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (cache de dependências)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY backend/ ./backend/

# Expor porta
EXPOSE 3000

# Variáveis de ambiente padrão
ENV PORT=3000
ENV HOST=0.0.0.0

# Comando para iniciar
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "3000"]
