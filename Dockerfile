FROM node:20-alpine

WORKDIR /app

# Copiar arquivos de dependências
COPY package*.json ./

# Instalar dependências
RUN npm ci --only=production

# Copiar código fonte
COPY server.js ./
COPY index.html ./
COPY kanban.html ./
COPY disparador.html ./

# Criar arquivo vazio de clientes (fallback)
RUN echo "{}" > clients.json

# Expor porta (Railway usa PORT env)
EXPOSE 3000

# Health check (usa 127.0.0.1 pois wget no Alpine resolve localhost para IPv6)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/health || exit 1

# Comando para iniciar
CMD ["node", "server.js"]
